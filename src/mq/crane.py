from enum import Enum

import serial


class ZMQTopics(Enum):
    """Enum for ZMQ topics"""

    DROP_LOAD = 1
    PICK_LOAD = 2
    RAISE_HOOK = 3
    DROP_HOOK = 4
    STATUS = 5
    VIDEO = 6
    PROCESSED_VIDEO = 7
    HELIPAD_GPS = 8
    TANK_GPS = 9


# This is a part of that is responsible for control of crane actuators
class CraneControls:
    def __init__(self, connection_string="/dev/ttyUSB0", baudrate=9600):
        self.ser = serial.Serial(connection_string, baudrate)
        self.ser.flushInput()
        self.hook_state = "dropped"  # Initial state of the hook

    def fetch_load(self):
        self.ser.write(b"Yuk Kaldir\n")
        line = self.ser.readline().decode("utf-8").strip()
        if line.startswith("Yuk:"):
            try:
                load = float(line.split(":")[1].strip())
                return load
            except ValueError:
                print("Error parsing load value:", line)
        return None

    def get_load(self):
        self.ser.write(b"Yuk Al\n")
        line = self.ser.readline().decode("utf-8").strip()
        if line.startswith("Yuk:"):
            try:
                load = float(line.split(":")[1].strip())
                return load
            except ValueError:
                print("Error parsing load value:", line)
        return None

    def get_state(self):
        self.ser.write(b"Durum\n")
        line = self.ser.readline().decode("utf-8").strip()
        if line.startswith("Durum:"):
            return line.split(":")[1].strip()
        return None

    def close(self):
        if self.ser.is_open:
            self.ser.close()
            print("Serial connection closed.")
        else:
            print("Serial connection is already closed.")

    def handle_command(self, command):
        if command == ZMQTopics.DROP_LOAD.name:
            return "ACK: Load dropped"
        elif command == ZMQTopics.PICK_LOAD.name:
            return "ACK: Load picked"
        elif command == ZMQTopics.RAISE_HOOK.name:
            if self.hook_state == "raised":
                return "ACK: Hook already raised"
            else:
                self.hook_state = "raised"
                return "ACK: Hook raised"
        elif command == ZMQTopics.DROP_HOOK.name:
            if self.hook_state == "dropped":
                return "ACK: Hook already dropped"
            else:
                self.hook_state = "dropped"
                return "ACK: Hook dropped"
        elif command == ZMQTopics.STATUS.name:
            return f"ACK: Hook is {self.hook_state}"
        else:
            return "NACK: Unknown command"
