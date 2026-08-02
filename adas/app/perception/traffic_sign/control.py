import time

try:
    from ...config import sign_config as cfg
except ImportError:
    from app.config import sign_config as cfg

try:
    from communication.protocol import UartProtocol
    from communication.uart import UartConfiguration
except ImportError:
    from ...communication.protocol import UartProtocol
    from ...communication.uart import UartConfiguration


class SignController:
    """Sends UART commands to the STM32 based on detected traffic signs.

    This controller operates independently from LaneController.
    The fusion state machine decides which controller is active.
    """

    def __init__(self, port=None, baudrate=None, timeout=None):
        # Sign-action parameters from config
        self.turn_left_steering = cfg.TURN_LEFT_STEERING
        self.turn_right_steering = cfg.TURN_RIGHT_STEERING
        self.turn_speed = cfg.TURN_SPEED

        self.stop_speed = cfg.STOP_SPEED
        self.stop_steering = cfg.STOP_STEERING

        # UART connection (same pattern as LaneController)
        self.uart = UartConfiguration(
            port=port or "/dev/ttyAMA0",
            baudrate=baudrate or 115200,
            timeout=timeout or 0.005,
        )
        self.uart_connected = self.uart.connect()

        self.last_send_time = time.time()
        self.last_stm32_response = None

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------
    def is_connected(self) -> bool:
        return (
            self.uart_connected
            and self.uart.serial_port is not None
            and self.uart.serial_port.is_open
        )

    def close(self):
        self.uart.close()
        self.uart_connected = False

    # ------------------------------------------------------------------
    # Core sign actions
    # ------------------------------------------------------------------
    def _send_command(self, cmd_id, speed, steering, brake):
        """Pack and send a single UART frame to the STM32."""
        steering = int(max(-100, min(100, steering)))
        packet = UartProtocol.pack_data(cmd_id, int(speed), steering, int(brake))
        if packet:
            self.uart.send_raw_bytes(packet)
            self.last_send_time = time.time()

    def execute_turn_left(self):
        """Steer the car to the left at a reduced speed."""
        self._send_command(
            cmd_id=1,
            speed=self.turn_speed,
            steering=self.turn_left_steering,
            brake=0,
        )

    def execute_turn_right(self):
        """Steer the car to the right at a reduced speed."""
        self._send_command(
            cmd_id=1,
            speed=self.turn_speed,
            steering=self.turn_right_steering,
            brake=0,
        )

    def execute_stop(self):
        """Bring the car to a full stop (speed=0, brake=1)."""
        self._send_command(
            cmd_id=1,
            speed=self.stop_speed,
            steering=self.stop_steering,
            brake=1,
        )

    # ------------------------------------------------------------------
    # Telemetry
    # ------------------------------------------------------------------
    def read_stm32_response(self):
        """Read the latest telemetry packet from the STM32."""
        raw = self.uart.read_raw_bytes(UartProtocol.RX_PACKET_SIZE)
        if raw and len(raw) == UartProtocol.RX_PACKET_SIZE:
            self.last_stm32_response = UartProtocol.unpack_data(raw)
        return self.last_stm32_response