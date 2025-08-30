import logging

import zmq


class ZMQClient:
    """ZMQ client for drone control commands"""

    def __init__(self, control_address: str, remote_control_address: str, _logger=None):
        self.control_address = control_address
        self.remote_control_address = remote_control_address
        if self.control_address is None or self.control_address == "":
            raise ValueError("Control address is not set")

        self.log = (
            _logger
            if callable(_logger)
            else lambda msg, level="info": print(f"[ZMQ Client][{level.upper()}] {msg}")
        )
        self.context = zmq.Context()
        self.socket = None
        self.remote_socket = None
        self.connected = False

        self.log(f"ZMQ Client initialized - Control: {self.control_address}", "info")

    def connect(self) -> bool:
        """Connect to ZMQ control server"""
        try:
            self.socket = self.context.socket(zmq.REQ)
            self.socket.connect(self.control_address)
            self.socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
            self.remote_socket = self.context.socket(zmq.REQ)
            self.remote_socket.connect(self.remote_control_address)
            self.remote_socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
            self.connected = True
            self.log(
                f"Connected to ZMQ control server at {self.control_address}", "info"
            )
            return True
        except Exception as e:
            self.log(f"Failed to connect to ZMQ control server: {e}", "error")
            self.connected = False
            return False

    def send_remote_command(self, command: str) -> str:
        """Send command to remote server and get response"""
        if not self.remote_socket or not self.connected:
            return "ERROR: Not connected"

        try:
            self.remote_socket.send_string(command)
            response = self.remote_socket.recv_string()
            # self.log(f"Command '{command}' -> Response: '{response}'", "info")
            return response
        except zmq.Again:
            return "ERROR: Timeout waiting for response"
        except Exception as e:
            self.log(f"Error sending command - REMOTE: ({command})- {e}", "error")
            return f"ERROR: {e}"

    def send_command(self, command: str) -> str:
        """Send command to server and get response"""
        if not self.socket or not self.connected:
            return "ERROR: Not connected"

        try:
            self.socket.send_string(command)
            response = self.socket.recv_string()
            # self.log(f"Command '{command}' -> Response: '{response}'", "info")
            return response
        except zmq.Again:
            return "ERROR: Timeout waiting for response"
        except Exception as e:
            self.log(f"Error sending command - LOCAL: ({command})- {e}", "error")
            return f"ERROR: {e}"

    def disconnect(self):
        """Disconnect from server"""
        self.connected = False
        if self.socket:
            self.socket.close()
        if self.remote_socket:
            self.remote_socket.close()
        self.context.term()
        self.log("Disconnected from ZMQ control server", "info")

    def is_connected(self) -> bool:
        """Check if connected to server"""
        return self.connected

    def start(self) -> bool:
        """Start ZMQ control connection"""
        control_connected = self.connect()

        if control_connected:
            self.log("ZMQ Client started", "info")
        else:
            self.log(
                "ZMQ Client failed to start - control connection failed", "warning"
            )

        return control_connected

    def stop(self):
        """Stop ZMQ control connection"""
        self.disconnect()
        self.log("ZMQ Client stopped", "info")


# Example usage
if __name__ == "__main__":
    import argparse

    import src.controls.mavlink.mission_types as mission_types

    logger = logging.getLogger(__name__)

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    config = mission_types.get_config()

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="ZMQ Control Client")
    parser.add_argument(
        "--control-address",
        default=config.control_address,
        help=f"ZMQ control address (default: {config.control_address})",
    )

    parser.add_argument(
        "--remote-control-address",
        default=config.remote_control_address,
        help=f"ZMQ remote control address (default: {config.remote_control_address})",
    )
    args = parser.parse_args()

    logger.info("Starting ZMQ control client")
    logger.info("Control Address: %s", args.control_address)
    logger.info("Remote Control Address: %s", args.remote_control_address)

    # Create ZMQ client
    client = ZMQClient(
        control_address=args.control_address,
        remote_control_address=args.remote_control_address,
    )

    # Connect and test commands
    if client.start():
        print("Connected successfully!")

        # Test some commands
        response = client.send_remote_command("HOOK_STATUS")
        if response.startswith("ACK>"):
            print("Remote Hook Status:", response[4:])
        else:
            print("Failed to get Remote Hook Status")

        response = client.send_command("HELIPAD_GPS")
        if response.startswith("ACK>"):
            coords = response[4:].split(",")
            helipad = float(coords[0]), float(coords[1])
            print(f"Helipad GPS: {helipad[0]}, {helipad[1]}")

        client.stop()
    else:
        print("Failed to connect to ZMQ server")
