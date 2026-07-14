import struct
import serial
import threading
from protocol import UartProtocol

class UartConfiguration:
    def __init__(self, port='/dev/ttyAMA0', baudrate=115200, timeout=0.01):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_port = None
        self.lock = threading.Lock()
        self.rx_buffer = bytearray()

    def connect(self) -> bool:
        with self.lock:
            try:
                self.serial_port = serial.Serial(
                    port=self.port, baudrate=self.baudrate, 
                    timeout=self.timeout, write_timeout=0
                )
                return True
            except serial.SerialException:
                return False

    def send_data(self, cmd_id: int, target_speed: int, steering_error: int, brake_command: int):
        data_bytes = UartProtocol.pack_data(cmd_id, target_speed, steering_error, brake_command)
        with self.lock:
            if self.serial_port and self.serial_port.is_open:
                try:
                    self.serial_port.write(data_bytes)
                except serial.SerialTimeoutException:
                    pass

    def read_latest_telemetry(self) -> dict:
        with self.lock:
            if not (self.serial_port and self.serial_port.is_open):
                return None
                
            in_waiting = self.serial_port.in_waiting
            if in_waiting > 0:
                self.rx_buffer.extend(self.serial_port.read(in_waiting))

        latest_data = None
        
        while len(self.rx_buffer) >= UartProtocol.RX_PACKET_SIZE:
            if self.rx_buffer[0] == UartProtocol.FRAME_HEADER_1 and self.rx_buffer[1] == UartProtocol.FRAME_HEADER_2:
                packet = self.rx_buffer[:UartProtocol.RX_PACKET_SIZE]
                parsed = UartProtocol.unpack_data(bytes(packet))
                if parsed:
                    latest_data = parsed
                self.rx_buffer = self.rx_buffer[UartProtocol.RX_PACKET_SIZE:]
            else:
                self.rx_buffer.pop(0)
                
        return latest_data

    def close(self):
        with self.lock:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()