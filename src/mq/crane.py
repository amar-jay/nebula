import time
from enum import Enum
import serial
import serial.tools.list_ports
import logging


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
    FPS = "FPS"


class CraneControls:
    """
    This is a part of that is responsible for control of crane actuators
    """

    def __init__(self, connection_string=None, baudrate=9600, timeout=1):
        """Initialize crane control with auto port detection
        Args:
            connection_string: Serial port path. If None, will auto-detect
            baudrate: Serial baudrate, defaults to 9600
            timeout: Serial timeout in seconds, defaults to 1
        """
        if connection_string is None:
            # Try to auto-detect Arduino port
            ports = list(serial.tools.list_ports.comports())
            for port in ports:
                if "Arduino" in port.description or "USB" in port.description:
                    connection_string = port.device
                    break
            if connection_string is None:
                raise ValueError("No Arduino device found! Available ports: " + str([p.device for p in ports]))

        try:
            self.ser = serial.Serial(connection_string, baudrate, timeout=timeout)
            time.sleep(2)  # Wait for Arduino to reset
            self.ser.flushInput()
            self.ser.flushOutput()
            self.hook_state = "raised"  # Initial state of the hook
            print(f"Connected to {connection_string}")
        except serial.SerialException as e:
            raise ConnectionError(f"Failed to connect to {connection_string}: {str(e)}")

    def _wait_for_ready(self, expected_response, timeout=10):
        """Wait for expected response with timeout
        Args:
            expected_response: Response string to wait for
            timeout: Maximum time to wait in seconds
        Returns:
            Response string if received, None if timeout
        """
        start_time = time.time()
        self.ser.flushInput()  # Clear any pending input

        while True:
            if time.time() - start_time > timeout:
                print(f"Timeout waiting for {expected_response}")
                return None

            if self.ser.in_waiting:  # Only try to read if there's data
                try:
                    response = self.ser.readline().decode().strip()
                    print(f"Response from crane: {response}")
                    if response == expected_response:
                        return response
                except UnicodeDecodeError:
                    print("Received invalid data")
                except serial.SerialException as e:
                    print(f"Serial error: {str(e)}")
                    return None

            time.sleep(0.1)

    def stop(self):
        """Send stop command and wait for acknowledgment"""
        command = "STOP"
        try:
            self.ser.write(f"{command}\n".encode())
            print("Waiting for crane to stop...")
            return True
        except serial.SerialException as e:
            print(f"Serial error during stop: {str(e)}")
            return False
        
    def pick_load(self):
        """Send pick load command and wait for acknowledgment"""
        command = "Yuk_Al"
        try:
            self.ser.write(f"{command}\n".encode())
            print("Waiting for crane to pick the load...")
            response = self._wait_for_ready("YUK_AL_TAMAM")

            if response == "YUK_AL_TAMAM":
                print("Yuk Al Görevi Tamamlandı.")
                print("Yeni göreve geçmeye hazırsınız.")
                self.hook_state = "raised"
                return True
            else:
                print("Failed to get confirmation from crane")
                return False
        except serial.SerialException as e:
            print(f"Serial error during pick_load: {str(e)}")
            return False

    def drop_load(self):
        """Send drop load command and wait for acknowledgment"""
        command = "Yuk_Birak"
        try:
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
        except serial.SerialException as e:
            print(f"Serial error during drop_load: {str(e)}")
            return False

    def close(self):
        """Safely close the serial connection"""
        if hasattr(self, 'ser') and self.ser.is_open:
            try:
                self.ser.close()
                print("Serial connection closed.")
            except serial.SerialException as e:
                print(f"Error closing serial connection: {str(e)}")
        else:
            print("Serial connection is already closed.")

    def handle_command(self, command):
        """Handle ZMQ commands
        Args:
            command: ZMQTopics command name
        Returns:
            Response string indicating success/failure
        """
        try:
            if command == ZMQTopics.DROP_LOAD.name:
                success = self.drop_load()
                return "ACK: Load dropped" if success else "NACK: Drop load failed"
            elif command == ZMQTopics.PICK_LOAD.name:
                success = self.pick_load()
                return "ACK: Load picked" if success else "NACK: Pick load failed"
            elif command == ZMQTopics.RAISE_HOOK.name:
                if self.hook_state == "raised":
                    return "ACK: Hook already raised"
                self.hook_state = "raised"
                return "ACK: Hook raised"
            elif command == ZMQTopics.DROP_HOOK.name:
                if self.hook_state == "dropped":
                    return "ACK: Hook already dropped"
                self.hook_state = "dropped"
                return "ACK: Hook dropped"
            elif command == ZMQTopics.STATUS.name:
                return f"ACK: Hook is {self.hook_state}"
            else:
                return "NACK: Unknown command"
        except Exception as e:
            return f"NACK: Error handling command: {str(e)}"


if __name__ == "__main__":
    # Try to auto-connect to Arduino
    try:
        crane = CraneControls()
        print("Connected to crane. Starting test sequence...")

        try:
            print("Testing pick load...")
            crane.pick_load()

            crane.stop()

            print("Testing drop load...")
            crane.drop_load()

        except KeyboardInterrupt:
            print("\nTest interrupted by user")
        except Exception as e:
            print(f"Error during test: {str(e)}")
        finally:
            crane.close()

    except (ValueError, ConnectionError) as e:
        print(f"Failed to initialize crane: {str(e)}")