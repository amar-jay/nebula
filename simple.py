#!/usr/bin/env python3

import logging
import time
# Enable INFO level logging by default so that INFO messages are shown
logging.basicConfig(level=logging.INFO)
from src.controls.mavlink import ardupilot


drone = ardupilot.ArdupilotConnection(
  connection_string="udp:127.0.0.1:16550",
)

def main():
    # drone.arm()
    time.sleep(2)
    drone.repeat_relay(count=2, delay=10)
    # time.sleep(2)
    # drone.repeat_relay(state=1, instance=2)
    # time.sleep(2)
    # drone.set_relay(state=0, instance=2)
    # time.sleep(2)
    # drone.set_relay(state=1, instance=2)
if __name__ == "__main__":
    main()