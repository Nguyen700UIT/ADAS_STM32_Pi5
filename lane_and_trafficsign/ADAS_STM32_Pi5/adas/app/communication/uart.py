import serial
import threading
from .protocol import UartProtocol


class UartConfiguration:
    """Thread-safe UART transport with a fail-safe command heartbeat.

    The STM32 watchdog expects a fresh command within 100 ms.  Vision
    inference is not real-time, so the latest command is retransmitted by a
    dedicated 50 Hz thread rather than relying on the camera loop cadence.
    """

    def __init__(self, port='/dev/ttyAMA0', baudrate=115200, timeout=0.01):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_port = None
        self.lock = threading.Lock()
        self.rx_buffer = bytearray()
        self._latest_telemetry = None
        self._latest_command = (1, 0, 0, 1)  # Safe default: emergency brake.
        self._heartbeat_stop = threading.Event()
        self._heartbeat_thread = None

    def connect(self) -> bool:
        with self.lock:
            try:
                self.serial_port = serial.Serial(
                    port=self.port, baudrate=self.baudrate, 
                    timeout=self.timeout, write_timeout=self.timeout
                )
                return True
            except serial.SerialException:
                return False

    def _write_frame_locked(self, data_bytes: bytes) -> bool:
        if not data_bytes or not (self.serial_port and self.serial_port.is_open):
            return False
        try:
            return self.serial_port.write(data_bytes) == len(data_bytes)
        except (serial.SerialException, serial.SerialTimeoutException):
            return False

    def send_data(self, cmd_id: int, target_speed: int, steering_error: int, brake_command: int) -> bool:
        """Store a command for the heartbeat and transmit it immediately."""
        data_bytes = UartProtocol.pack_data(cmd_id, target_speed, steering_error, brake_command)
        if not data_bytes:
            return False
        with self.lock:
            self._latest_command = (
                int(cmd_id), int(target_speed), int(steering_error), int(brake_command)
            )
            return self._write_frame_locked(data_bytes)

    def start_heartbeat(self, period_s: float = 0.02) -> None:
        """Retransmit the latest command at a fixed cadence (default: 50 Hz)."""
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            return

        self._heartbeat_stop.clear()

        def _run():
            while not self._heartbeat_stop.is_set():
                with self.lock:
                    frame = UartProtocol.pack_data(*self._latest_command)
                    self._write_frame_locked(frame)
                self._heartbeat_stop.wait(period_s)

        self._heartbeat_thread = threading.Thread(
            target=_run, name="uart-command-heartbeat", daemon=True
        )
        self._heartbeat_thread.start()

    def stop_heartbeat(self) -> None:
        self._heartbeat_stop.set()
        if self._heartbeat_thread and self._heartbeat_thread is not threading.current_thread():
            self._heartbeat_thread.join(timeout=0.2)
        self._heartbeat_thread = None

    def read_latest_telemetry(self) -> dict:
        with self.lock:
            if not (self.serial_port and self.serial_port.is_open):
                return self.get_latest_telemetry()

            try:
                in_waiting = self.serial_port.in_waiting
                if in_waiting > 0:
                    self.rx_buffer.extend(self.serial_port.read(in_waiting))
            except serial.SerialException:
                return self.get_latest_telemetry()

            latest_data = None
            
            while len(self.rx_buffer) >= UartProtocol.RX_PACKET_SIZE:
                if self.rx_buffer[0] == UartProtocol.FRAME_HEADER_1 and self.rx_buffer[1] == UartProtocol.FRAME_HEADER_2:
                    packet = self.rx_buffer[:UartProtocol.RX_PACKET_SIZE]
                    parsed = UartProtocol.unpack_data(bytes(packet))
                    if parsed:
                        latest_data = parsed
                        self._latest_telemetry = parsed
                        self.rx_buffer = self.rx_buffer[UartProtocol.RX_PACKET_SIZE:]
                    else:
                        self.rx_buffer.pop(0)
                else:
                    self.rx_buffer.pop(0)
                    
            return dict(latest_data) if latest_data else self.get_latest_telemetry()

    def get_latest_telemetry(self) -> dict:
        """Return cached telemetry without consuming serial input."""
        return dict(self._latest_telemetry) if self._latest_telemetry else None

    def close(self):
        self.stop_heartbeat()
        with self.lock:
            if self.serial_port and self.serial_port.is_open:
                # Best effort: leave the actuator in a safe state before closing.
                self._write_frame_locked(UartProtocol.pack_data(1, 0, 0, 1))
                self.serial_port.close()
