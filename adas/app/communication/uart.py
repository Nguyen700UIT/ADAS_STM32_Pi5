
import serial
class UartConfiguration:
    def __init__(self, port='/dev/ttyAMA0', baudrate=115200, timeout=0.5):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_port = None

    def connect(self):
        try:
            self.serial_port = serial.Serial(
                port = self.port,
                baudrate = self.baudrate,
                bytesize = serial.EIGHTBITS,
                parity = serial.PARITY_NONE,
                stopbits = serial.STOPBITS_ONE,
                timeout = self.timeout
            )
            return True
        except serial.SerialException as e:
            return False

    def send_raw_bytes(self, data_bytes: bytes):
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.write(data_bytes)
                return True
            except Exception as e:
                return False
        else:
            return False

    def read_raw_bytes(self, num_bytes: int) -> bytes:
        if self.serial_port and self.serial_port.is_open:
            try:
                return self.serial_port.read(num_bytes)
            except Exception as e:
                return b""
        return b""

    def close(self):
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()