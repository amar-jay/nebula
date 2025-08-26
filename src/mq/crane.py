import time
from enum import Enum

import serial


class ZMQTopics(Enum):
    """Enum for ZMQ topics"""

    DROP_LOAD = "DROP_LOAD"
    PICK_LOAD = "PICK_LOAD"
    RAISE_HOOK = "RAISE_HOOK"
    DROP_HOOK = "DROP_HOOK"
    STATUS = "STATUS"
    VIDEO = "VIDEO"
    PROCESSED_VIDEO = "PROCESSED_VIDEO"
    HELIPAD_GPS = "HELIPAD_GPS"
    TANK_GPS = "TANK_GPS"


class CraneControls:
    """
    This is a part of that is responsible for control of crane actuators
    """

    def __init__(self, connection_string="/dev/ttyUSB0", baudrate=9600):
        self.ser = serial.Serial(connection_string, baudrate)
        self.ser.flushInput()
        self.hook_state = "raised"  # Initial state of the hook

    def _wait_for_ready(self, expected_response):
        while True:
            response = self.ser.readline().decode().strip()
            if response == expected_response:
                return expected_response
            else:
                time.sleep(0.1)

    def pick_load(self):
        command = "Yuk_Al"
        self.ser.write(f"{command}\n".encode())
        response = self._wait_for_ready("YUK_AL_TAMAM")
        if response == "YUK_AL_TAMAM":
            print("Yuk Al Görevi Tamamlandı.")
            print("Yeni göreve geçmeye hazırsınız.")
            self.hook_state = "raised"
        return True

    def drop_load(self):
        command = "Yuk_Birak"
        self.ser.write(f"{command}\n".encode())
        response = self._wait_for_ready("YUK_BIRAK_TAMAM")
        if response == "YUK_BIRAK_TAMAM":
            print("Yuk Birak Görevi Tamamlandı.")
            print("Yeni göreve geçmeye hazırsınız.")
            self.hook_state = "dropped"
            return True
        else:
            print("Bir hata oluştu, lütfen tekrar deneyin.")
        return False

    def close(self):
        if self.ser.is_open:
            self.ser.close()
            print("Serial connection closed.")
        else:
            print("Serial connection is already closed.")

    def handle_command(self, command):
        if command == ZMQTopics.DROP_LOAD.name:
            self.drop_load()
            return "ACK: Load dropped"
        elif command == ZMQTopics.PICK_LOAD.name:
            self.pick_load()
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
