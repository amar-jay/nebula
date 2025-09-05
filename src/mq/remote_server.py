import argparse
import logging
import os
import time

import zmq

from src.controls.logger import init_logging
from src.controls.mavlink import mission_types
from src.mq.crane import CraneControls, ExampleController
from src.mq.mavproxy_tcp import MAVLinkProxy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("remote_zmq_server")
# Setup logging


logger = init_logging(
    level=logging.DEBUG,
    log_file=os.path.join(os.path.expanduser("~"), "local-zmq-server.log"),
)


class RemoteZMQServer:
    """ZMQ Server for handling crane control commands"""

    def __init__(
        self,
        is_simulation: bool,
        remote_control_address: str,
        mavproxy_source: str,
        controller_address: str,
        baudrate: int,
    ):
        self.remote_control_address = remote_control_address
        self.controller_address = controller_address
        self.baudrate = baudrate
        self.running = False
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)  # Reply socket
        self.LISTEN_ADDR = "0.0.0.0"
        self.LISTEN_PORT = 16550
        self.TARGET_ADDR, self.TARGET_PORT = mavproxy_source.split(":")[1:]
        self.LISTEN_PORT = int(self.LISTEN_PORT)

        # Initialize crane controls
        if is_simulation:
            self.crane = ExampleController()
        else:
            self.crane = CraneControls(
                connection_string=controller_address, baudrate=baudrate
            )

        logger.info(
            f"ZMQ Crane Server initialized on port {self.remote_control_address}"
        )
        self.proxy = MAVLinkProxy(connection_string=mavproxy_source, logger=logger)
        logger.info(
            f"Listening on {self.LISTEN_ADDR}:{self.LISTEN_PORT}, forwarding to {self.TARGET_ADDR}:{self.TARGET_PORT}"
        )

    def start(self):
        """Start the ZMQ server"""
        try:
            self.proxy.start()
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

    def stop(self):
        """Stop the server gracefully"""
        logger.info("Stopping server...")
        self.running = False

    def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up resources...")
        self.crane.close()
        self.socket.close()
        self.context.term()
        self.proxy.close()
        logger.info("Server stopped")


def main():
    """Main function to start the server"""

    parser = argparse.ArgumentParser(description="Remote ZMQ Crane Control Server")
    parser.add_argument(
        "--config-path",
        type=str,
        default=mission_types.CONFIG_PATH,
        help=f"Path to the configuration file (default: {mission_types.CONFIG_PATH})",
    )
    parser.add_argument(
        "--is-simulation",
        action="store_true",
        help="Run in simulation mode (default: False)",
    )
    args = parser.parse_args()
    if args.is_simulation:
        import os

        args.config_path = os.path.join(
            os.path.dirname(args.config_path), "simulation.yaml"
        )
    config = mission_types.get_config(args.config_path)

    server = RemoteZMQServer(
        is_simulation=args.is_simulation,
        remote_control_address=config.remote_control_address,
        controller_address=config.controller_connection_string,
        baudrate=config.controller_baudrate,
        mavproxy_source=config.mavproxy_source,
    )

    try:
        server.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        server.stop()


if __name__ == "__main__":
    main()
