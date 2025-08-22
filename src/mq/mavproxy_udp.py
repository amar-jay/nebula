import logging
import socket
import threading
import time

from src.controls.mavlink import ardupilot, mission_types


class MAVLinkProxy:
    """Handles MAVLink connection and UDP proxy in a clean way"""

    def __init__(
        self,
        connection_string: str,
        host: str = "0.0.0.0",
        port: int = 16550,
        logger: logging.Logger = None,
    ):
        self.connection_string = connection_string
        self.udp_host = host
        self.udp_port = port
        self.connection = None
        self.udp_socket = None
        self.clients: set[tuple[str, int]] = set()
        self.clients_lock = threading.Lock()
        self.running = False
        self._drone_data = mission_types.FrameData()
        self.logger = logger or logging.getLogger(__name__)

    def start(self):
        # Initialize MAVLink connection
        try:
            self.connection = ardupilot.ArdupilotConnection(
                connection_string=self.connection_string
            )
            self.logger.info("MAVLink connection established")
        except ConnectionError:
            self.logger.error(
                "Failed to connect to MAVLink at %s", self.connection_string
            )
            raise

        # Set up UDP server
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_socket.bind((self.udp_host, self.udp_port))
        self.logger.info("UDP server listening on %s:%d", self.udp_host, self.udp_port)

        self.running = True

        # Start background threads
        threading.Thread(target=self._handle_clients, daemon=True).start()
        threading.Thread(target=self._forward_proxy_across_udp, daemon=True).start()

    def close(self):
        self.running = False
        if self.udp_socket:
            self.udp_socket.close()
        if self.connection:
            self.connection.close()
        with self.clients_lock:
            self.clients.clear()

    def get_drone_data(self) -> mission_types.FrameData | None:
        # if all the data is not available then its the mavlink connection issue
        if (
            not self._drone_data.drone_position
            and not self._drone_data.drone_attitude
            and not self._drone_data.ground_level
        ):
            self.logger.warning("Drone data not available. Waiting for mavlink data...")
            return None

        if not self._drone_data.drone_position:
            self.logger.warning("Drone position not available")
            return None
        if not self._drone_data.drone_attitude:
            self.logger.warning("Drone attitude not available")
            return None
        if not self._drone_data.ground_level:
            self.logger.warning("Ground level not available")
            return None

        return self._drone_data

    def _fetch_drone_data(self, msg):
        """Get current drone position, attitude, and ground level"""
        if not self.connection:
            self.logger.warning("MAVLink connection not established")
            return

        msg_type = msg.get_type()

        if msg_type == "GLOBAL_POSITION_INT":
            # Convert values to standard units
            lat = msg.lat / 1e7
            lon = msg.lon / 1e7
            relative_alt: float = msg.relative_alt / 1000.0  # meters
            alt_amsl: float = msg.alt / 1000.0  # meters

            self._drone_data.drone_position = (lat, lon, alt_amsl)
            self._drone_data.ground_level = alt_amsl - relative_alt
            self._drone_data.mode = self.connection.get_mode()
            return
        elif msg_type == "ATTITUDE":
            roll = msg.roll
            pitch = msg.pitch
            yaw = msg.yaw

            # Normalize yaw to [0, 2π]
            pi = 3.141592653589793
            if yaw < 0:
                yaw += 2 * pi

            self._drone_data.drone_attitude = (roll, pitch, yaw)
        self._drone_data.mode = self.connection.get_mode()
        self._drone_data.timestamp = time.time()

    def _handle_clients(self):
        while self.running:
            try:
                # Set socket to non-blocking
                self.udp_socket.settimeout(0.001)

                try:
                    data, client_address = self.udp_socket.recvfrom(1024)

                    # Register new client
                    with self.clients_lock:
                        self.clients.add(client_address)

                    # Forward message to MAVLink connection
                    if self.connection and data:
                        self.connection.master.write(data)

                except socket.timeout:
                    # No message available, continue
                    pass

            except Exception as e:
                if self.running:
                    self.logger.error("Error handling clients: %s", e)
                    time.sleep(0.1)

    def _forward_proxy_across_udp(self):
        while self.running:
            try:
                if not self.connection:
                    time.sleep(0.1)
                    continue

                msg = self.connection.master.recv_match(blocking=False)
                if msg is not None:
                    # Fetch drone data for gps estimation
                    self._fetch_drone_data(msg)

                    msg_bytes = msg.get_msgbuf()

                    with self.clients_lock:
                        disconnected_clients = []
                        for client_address in self.clients.copy():
                            try:
                                self.udp_socket.sendto(msg_bytes, client_address)
                            except Exception:
                                disconnected_clients.append(client_address)

                        for client_address in disconnected_clients:
                            self.clients.discard(client_address)
                else:
                    time.sleep(0.001)  # Small sleep when no messages

            except Exception as e:
                self.logger.error(f"Error in serial to UDP forwarding: {e}")
                time.sleep(0.1)
