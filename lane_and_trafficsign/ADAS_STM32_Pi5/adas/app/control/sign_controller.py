import time

try:
    from ...config import sign_config as cfg
except ImportError:
    from config import sign_config as cfg

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

    def __init__(self, port=None, baudrate=None, timeout=None, uart=None):
        # Sign-action parameters from config
        self.turn_left_steering = cfg.TURN_LEFT_STEERING
        self.turn_right_steering = cfg.TURN_RIGHT_STEERING
        self.turn_speed = cfg.TURN_SPEED

        self.stop_speed = cfg.STOP_SPEED
        self.stop_steering = cfg.STOP_STEERING

        # EMA ramp rates
        self.steering_ramp_alpha = cfg.STEERING_RAMP_ALPHA
        self.speed_ramp_alpha = cfg.SPEED_RAMP_ALPHA

        # Smoothed current values (start at neutral)
        self.current_steering = 0.0
        self.current_speed = 0.0

        # UART connection (same pattern as LaneController) or shared
        if uart is not None:
            self.uart = uart
            self.uart_connected = getattr(self.uart, 'serial_port', None) is not None and self.uart.serial_port.is_open
        else:
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
    def _ramp(self, current, target, alpha):
        """Exponential moving average: blend *current* toward *target*."""
        return alpha * target + (1.0 - alpha) * current

    def _send_command(self, cmd_id, target_speed, target_steering, brake):
        """Ramp toward *target_speed* / *target_steering*, then send."""
        self.current_steering = self._ramp(
            self.current_steering, target_steering, self.steering_ramp_alpha
        )
        self.current_speed = self._ramp(
            self.current_speed, target_speed, self.speed_ramp_alpha
        )

        steering_out = int(max(-100, min(100, round(self.current_steering))))
        speed_out = int(max(0, round(self.current_speed)))

        self.uart.send_data(cmd_id, speed_out, steering_out, int(brake))
        self.last_send_time = time.time()

    def execute_turn_left(self):
        """Ramp steering toward full left at a reduced speed."""
        self._send_command(
            cmd_id=1,
            target_speed=self.turn_speed,
            target_steering=self.turn_left_steering,
            brake=0,
        )

    def execute_turn_right(self):
        """Ramp steering toward full right at a reduced speed."""
        self._send_command(
            cmd_id=1,
            target_speed=self.turn_speed,
            target_steering=self.turn_right_steering,
            brake=0,
        )

    def execute_stop(self):
        """Ramp speed down to zero and engage brake."""
        self._send_command(
            cmd_id=1,
            target_speed=self.stop_speed,
            target_steering=self.stop_steering,
            brake=1,
        )

    def execute_idle(self):
        """Maintain communication and ramp toward neutral (idle state)."""
        self._send_command(
            cmd_id=1,
            target_speed=0,
            target_steering=0,
            brake=0,
        )

    def reset(self):
        """Reset smoothed values to neutral (call on state transitions)."""
        self.current_steering = 0.0
        self.current_speed = 0.0

    # ------------------------------------------------------------------
    # Telemetry
    # ------------------------------------------------------------------
    def read_stm32_response(self):
        """Read the latest telemetry packet from the STM32."""
        resp = self.uart.read_latest_telemetry()
        if resp is not None:
            self.last_stm32_response = resp
        return self.last_stm32_response