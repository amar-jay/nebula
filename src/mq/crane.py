import logging
import time
from enum import Enum

import serial
import serial.tools.list_ports


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

    def __init__(self, connection_string=None, baudrate=9600):
        """Initialize crane control with auto port detection
        Args:
            connection_string: Serial port path. If None, will auto-detect
            baudrate: Serial baudrate, defaults to 9600
        """
        if connection_string is None:
            # Try to auto-detect Arduino port
            ports = list(serial.tools.list_ports.comports())
            for port in ports:
                if "Arduino" in port.description or "USB" in port.description:
                    connection_string = port.device
                    break
            if connection_string is None:
                raise ValueError(
                    "No Arduino device found! Available ports: "
                    + str([p.device for p in ports])
                )

        try:
            self.ser = serial.Serial(connection_string, baudrate)
            time.sleep(2)  # Wait for Arduino to reset
            self.ser.flushInput()
            self.ser.flushOutput()
            self.hook_state = "raised"  # Initial state of the hook
            print(f"Connected to {connection_string}")
        except serial.SerialException as e:
            raise ConnectionError(f"Failed to connect to {connection_string}: {str(e)}")

    def _wait_for_ready(self, expected_response):
        """Wait for expected response indefinitely
        Args:
            expected_response: Response string to wait for
        Returns:
            Response string if received, None if error occurs
        """
        self.ser.flushInput()  # Clear any pending input

        while True:

            if self.manual_override and self.override_confirmation == expected_response:
                print(f"Manual override confirmed: {expected_response}")
                self.override_confirmation = None
                self.manual_override = False
                return expected_response

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


    def enable_manual_override(self):
        print("Manual override activated!")
        self.manual_override = True
        self.stop()  # vinci hemen durdur


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
            elif self.manual_override:
                print("Manual override: Operator controlled the hook.")
                print("Assuming YUK_AL_TAMAM")
                self.hook_state = "raised"
                self.manual_override = False  # override bitti
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
            elif self.manual_override:
                print("Manual override: Operator controlled the hook.")
                print("Assuming YUK_AL_TAMAM")
                self.hook_state = "raised"
                self.manual_override = False  # override bitti
                return True
            else:
                print("Bir hata oluştu, lütfen tekrar deneyin.")
                return False
        except serial.SerialException as e:
            print(f"Serial error during drop_load: {str(e)}")
            return False
        
    def manuel_yukari(self):
        """Send command to manually move hook up"""
        crane.stop()  # vinci hemen durdur
        try:
            self.ser.write("Manuel Y\n".encode())
            print("Kanca manuel olarak yukarı kaldırılıyor...")
            return True
        except serial.SerialException as e:
            print(f"Serial error during manuel_yukari: {str(e)}")
            return False

    def manuel_asagi(self):
        """Send command to manually move hook down"""
        crane.stop()  # vinci hemen durdur
        try:
            self.ser.write("Manuel A\n".encode())
            print("Kanca manuel olarak aşağı indiriliyor...")
            return True
        except serial.SerialException as e:
            print(f"Serial error during manuel_asagi: {str(e)}")
            return False
        
    def yuk_al_tamam(self):
        """Operatör onayı: yük alındı"""
        self.override_confirmation = "YUK_AL_TAMAM"
        print("✅ Operatör: Yük alındı onayı verildi.")


    def yuk_birak_tamam(self):
        """Operatör onayı: yük bırakıldı"""
        self.override_confirmation = "YUK_BIRAK_TAMAM"
        print("✅ Operatör: Yük bırakıldı onayı verildi.")
        
    def close(self):
        """Safely close the serial connection"""
        if hasattr(self, "ser") and self.ser.is_open:
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
            elif command == "MANUAL_OVERRIDE":
                self.enable_manual_override()
                return "ACK: Manual override enabled"
            elif command == "MANUEL Y":
                success = self.manuel_yukari()
                return "ACK: Hook moving up" if success else "NACK: Failed to move hook up"
            elif command == "MANUEL A":
                success = self.manuel_asagi()
                return "ACK: Hook moving down" if success else "NACK: Failed to move hook down"
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

class ExampleController:
    """
    Simulated controller for testing without real serial hardware.
    Uses user input to mimic crane responses.
    """

    def __init__(self):
        self.hook_state = "raised"
        print("ExampleController initialized (simulation mode).")

    def _wait_for_ready(self, expected_response, timeout=10):
        print(f"Simulating wait for '{expected_response}' (timeout {timeout}s)...")
        response = input(f"Type 'y' to simulate response: ").strip()
        if response == "y":
            print(f"Simulated response received: {expected_response}")
            return expected_response
        print("Simulated timeout or wrong response.")
        return None

    def stop(self):
        print("Simulating STOP command.")
        input("Press Enter to simulate crane stopped...")
        return True

    def pick_load(self):
        print("Simulating pick load command.")
        response = self._wait_for_ready("YUK_AL_TAMAM")
        if response == "YUK_AL_TAMAM":
            print("Simulated: Yuk Al Görevi Tamamlandı.")
            self.hook_state = "raised"
            return True
        print("Simulated: Failed to get confirmation.")
        return False

    def drop_load(self):
        print("Simulating drop load command.")
        response = self._wait_for_ready("YUK_BIRAK_TAMAM")
        if response == "YUK_BIRAK_TAMAM":
            print("Simulated: Yuk Birak Görevi Tamamlandı.")
            self.hook_state = "dropped"
            return True
        print("Simulated: Bir hata oluştu.")
        return False

    def close(self):
        print("Simulated: Controller closed.")

    def handle_command(self, command):
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