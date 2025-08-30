import argparse
import logging
import time

import zmq

from src.controls.mavlink import mission_types
from src.mq.crane import CraneControls

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("remote_zmq_server")


class RemoteZMQServer:
    """ZMQ Server for handling crane control commands"""

    def __init__(
        self,
        remote_control_address: str,
        controller_address: str,
        baudrate: int,
    ):
        self.remote_control_address = remote_control_address
        self.controller_address = controller_address
        self.baudrate = baudrate
        self.running = False
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)  # Reply socket

        # Initialize crane controls
        self.crane = CraneControls(self.controller_address, self.baudrate)

        logger.info(
            f"ZMQ Crane Server initialized on port {self.remote_control_address}"
        )

    def start_server(self):
        """Start the ZMQ server"""
        try:
            self.socket.bind(self.remote_control_address)
            logger.info(f"Server listening on port {self.remote_control_address}")
            self.running = True

            while self.running:
                try:
                    # Wait for next request from client
                    message = self.socket.recv_string(zmq.NOBLOCK)
                    logger.info(f"Received request: {message}")

                    # Process the command
                    # Handle crane command
                    response = self.crane.handle_command(message)

                    # Send reply back to client
                    self.socket.send_string(response)
                    logger.info(f"Recieved: {message} / Sent response: {response}")

                except zmq.Again:
                    # No message available, continue
                    time.sleep(0.01)
                    continue
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    try:
                        self.socket.send_string("NACK: Server error")
                    except:
                        pass

        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            self.cleanup()

    def stop_server(self):
        """Stop the server gracefully"""
        logger.info("Stopping server...")
        self.running = False

    def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up resources...")
        self.crane.close()
        self.socket.close()
        self.context.term()
        logger.info("Server stopped")


def main():
    """Main function to start the server"""

    config = mission_types.get_config()
    ccs = config.controller_connection_string

    if not ccs:
        ccs = "tcp://localhost:5556"

    parser = argparse.ArgumentParser(description="ZMQ Crane Control Server")
    parser.add_argument(
        "--remote-control-address",
        type=str,
        default=config.remote_control_address,
        help="Remote control address",
    )
    parser.add_argument(
        "--controller-address", type=str, default=ccs, help="Controller address"
    )
    parser.add_argument(
        "--baudrate",
        type=int,
        default=config.controller_baudrate,
        help="Serial baudrate",
    )

    args = parser.parse_args()

    server = RemoteZMQServer(
        remote_control_address=args.remote_control_address,
        controller_address=args.controller_address,
        baudrate=args.baudrate,
    )

    try:
        server.start_server()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        server.stop_server()


if __name__ == "__main__":
    main()
