import logging
import socket
import threading
import time

import numpy as np

from src.controls.mavlink import ardupilot
from src.controls.mavlink.mission_types import FrameData


class MAVLinkProxy:
    """Handles MAVLink connection and TCP proxy in a clean way"""

    def __init__(
        self,
        connection_string: str,
        host: str = "0.0.0.0",
        port: int = 16550,
        logger: logging.Logger = None,
    ):
        self.connection_string = connection_string
        self.tcp_host = host
        self.tcp_port = port
        self.connection = None
        self.tcp_server = None
        self.clients: list[socket.socket] = []
        self.clients_lock = threading.Lock()
        self.running = False
        self.drone_data = FrameData()
        self.logger = logger or logging.getLogger(__name__)

    def start(self):
        # Initialize MAVLink connection
        try:
            self.connection = ardupilot.ArdupilotConnection(
                connection_string=self.connection_string,
                logger=self.logger,
            )
            self.logger.info("MAVLink connection established")
        except ConnectionError:
            self.logger.error(
                "Failed to connect to MAVLink at %s", self.connection_string
            )
            raise

        # Set up TCP server
        self.tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_server.bind((self.tcp_host, self.tcp_port))
        self.tcp_server.listen(5)
        self.logger.info("TCP server listening on %s:%d", self.tcp_host, self.tcp_port)

        self.running = True

        # Start background threads
        threading.Thread(target=self._accept_clients, daemon=True).start()
        threading.Thread(target=self._forward_proxy_across_tcp, daemon=True).start()

    def close(self):
        self.running = False
        if self.tcp_server:
            self.tcp_server.close()
        if self.connection:
            self.connection.close()
        with self.clients_lock:
            for client in self.clients:
                try:
                    client.close()
                except Exception:
                    self.logger.warning("Failed to close client socket")
            self.clients.clear()

    def get_drone_data(self) -> FrameData | None:
        # if all the data is not available then its the mavlink connection issue
        if (
            not self.drone_data.drone_position
            and not self.drone_data.drone_attitude
            and not self.drone_data.ground_level
        ):
            self.logger.warning("Drone data not available. Waiting for mavlink data...")
            return None

        if not self.drone_data.drone_position:
            self.logger.warning("Drone position not available")
            return None
        if not self.drone_data.drone_attitude:
            self.logger.warning("Drone attitude not available")
            return None
        if not self.drone_data.ground_level:
            self.logger.warning("Ground level not available")
            return None

        return FrameData(
            drone_attitude=self.drone_data.drone_attitude,
            drone_position=self.drone_data.drone_position,
            ground_level=self.drone_data.ground_level,
            mode=self.drone_data.mode,
        )

    def fetch_drone_data(self, msg):
        """Get current drone position, attitude, and ground level"""
        if not self.connection:
            self.logger.warning("MAVLink connection not established")
            return

        msg_type = msg.get_type()

        if msg_type == "GLOBAL_POSITION_INT":
            # Convert values to standard units
            lat = msg.lat / 1e7
            lon = msg.lon / 1e7
            relative_alt = msg.relative_alt / 1000.0  # meters
            alt_amsl = msg.alt / 1000.0  # meters

            self.drone_data.drone_position = (lat, lon, alt_amsl)
            self.drone_data.ground_level = alt_amsl - relative_alt

        elif msg_type == "ATTITUDE":
            roll = msg.roll
            pitch = msg.pitch
            yaw = msg.yaw

            # Normalize yaw to [0, 2π]
            if yaw < 0:
                yaw += 2 * np.pi

            self.drone_data.drone_attitude = (roll, pitch, yaw)

        self.drone_data.mode = self.connection.get_mode()

    def _accept_clients(self):
        while self.running:
            try:
                client_socket, client_address = self.tcp_server.accept()
                with self.clients_lock:
                    self.clients.append(client_socket)
                self.logger.info("New client connected: %s", client_address)

                # Handle client in separate thread
                threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, client_address),
                    daemon=True,
                ).start()
            except Exception as e:
                if self.running:
                    self.logger.error("Error accepting client: %s", e)
                    time.sleep(1)

    def _handle_client(self, client_socket: socket.socket, client_address: tuple):
        try:
            while self.running:
                try:
                    data = client_socket.recv(1024)
                    if not data:
                        break
                    if self.connection:
                        self.connection.master.write(data)
                except Exception as e:
                    self.logger.error(f"Error handling client {client_address}: {e}")
                    break
        finally:
            with self.clients_lock:
                if client_socket in self.clients:
                    self.clients.remove(client_socket)
            client_socket.close()
            self.logger.info(f"Client disconnected: {client_address}")

    def _forward_proxy_across_tcp(self):
        while self.running:
            try:
                if not self.connection:
                    time.sleep(0.1)
                    continue

                msg = self.connection.master.recv_match(blocking=False)
                if msg is not None:
                    # Fetch drone data for gps estimation
                    self.fetch_drone_data(msg)

                    msg_bytes = msg.get_msgbuf()

                    with self.clients_lock:
                        disconnected_clients: list[socket.socket] = []
                        for client in self.clients:
                            try:
                                client.send(msg_bytes)
                            except Exception:
                                disconnected_clients.append(client)

                        for client in disconnected_clients:
                            self.clients.remove(client)
                            try:
                                client.close()
                            except:
                                pass
                else:
                    time.sleep(0.001)  # Small sleep when no messages

            except Exception as e:
                self.logger.error(f"Error in serial to TCP forwarding: {e}")
                time.sleep(0.1)
