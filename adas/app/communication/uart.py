import serial
import threading

class UartConfiguration:
    def __init__(self, port='/dev/ttyAMA0', baudrate=115200, timeout=0.02):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout 
        self.serial_port = None
        self.lock = threading.Lock() 

    def connect(self):
        with self.lock:
            try:
                self.serial_port = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=self.timeout
                )
                return True
            except serial.SerialException:
                return False

    def send_raw_bytes(self, data_bytes: bytes):
        with self.lock:
            if self.serial_port and self.serial_port.is_open:
                try:
                    self.serial_port.write(data_bytes)
                    self.serial_port.flush()
                    return True
                except Exception:
                    return False
            return False

    def read_raw_bytes(self, num_bytes: int) -> bytes:
        with self.lock:
            if self.serial_port and self.serial_port.is_open:
                try:
                    if self.serial_port.in_waiting >= num_bytes:
                        return self.serial_port.read(num_bytes)
                    else:
                        return b"" 
                except Exception:
                    return b""
            return b""

    def close(self):
        with self.lock:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()