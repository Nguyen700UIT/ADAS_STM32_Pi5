

import time
import numpy as np

try:
    from . import lane_control_config as cfg
except ImportError:
    import lane_control_config as cfg

try:
    from communication.protocol import UartProtocol
    from communication.uart import UartConfiguration
except ImportError:
    from ...communication.protocol import UartProtocol
    from ...communication.uart import UartConfiguration


class LaneController:
    def __init__(self, port=None, baudrate=None, timeout=None):

        self.img_center = cfg.IMG_CENTER
        self.lookahead_points_y = cfg.LOOKAHEAD_POINTS_Y
        self.lookahead_weights = cfg.LOOKAHEAD_POINTS_WEIGHTS
        self.n_lookahead = len(self.lookahead_points_y)

        self.servo_center = cfg.SERVO_CENTER
        self.max_steering_angle = cfg.MAX_STEERING_ANGLE
        self.min_steering_angle = cfg.MIN_STEERING_ANGLE
        self.steering_gain = cfg.STEERING_GAIN

        self.straight_radius = cfg.STRAIGHT_RADIUS
        self.curve_radius = cfg.CURVE_RADIUS
        self.sharp_curve_radius = cfg.SHARP_CURVE_RADIUS

        self.max_speed = cfg.MAX_SPEED
        self.normal_speed = cfg.NORMAL_SPEED
        self.low_speed = cfg.LOW_SPEED

        self.offset_deadband = cfg.OFFSET_DEADBAND
        self.lane_change_offset = cfg.LANE_CHANGE_OFFSET

        self.steering_ema_alpha = cfg.STEERING_EMA_ALPHA


        self.uart = UartConfiguration(
            port=port or "/dev/ttyAMA0",
            baudrate=baudrate or 115200,
            timeout=timeout or 0.5,
        )
        self.uart_connected = self.uart.connect()

        self.offset = 0
        self.smoothed_steering = 0.0            # EMA-smoothed steering angle
        self.consecutive_departure = 0           # Frames since departure flag set
        self.frame_counter = 0                   # Counter for transmission rate
        self.last_send_time = time.time()        # For rate limiting
        self.last_stm32_response = None          # Most recent STM32 telemetry

    def is_connected(self) -> bool:
        return self.uart_connected and self.uart.serial_port is not None and self.uart.serial_port.is_open

    def close(self):
        self.uart.close()
        self.uart_connected = False

    def calc_offset(self, center_fitx, ploty):
        """
        Compute blended lateral offset using weighted lookahead points.

        For each lookahead y-position in LOOKAHEAD_POINTS_Y:
            1. Find the closest y-index in ploty
            2. Get the lane center x at that index from center_fitx
            3. Compute offset = center_x - img_center
            4. Multiply by the lookahead weight
            5. Sum all weighted offsets

        A deadband is applied to the final blended offset.

        Args:
            center_fitx: Lane center x-positions for all y in ploty.
            ploty: y-coordinates corresponding to center_fitx.

        Returns:
            Blended offset in pixels (float).
            Positive = right of center, Negative = left of center.
        """
        blended_offset = 0.0

        for lookahead_y, weight in zip(self.lookahead_points_y, self.lookahead_weights):
            # Find the index in ploty closest to the target lookahead y
            idx = np.argmin(np.abs(ploty - lookahead_y))
            lane_center_x = center_fitx[idx]
            offset = lane_center_x - self.img_center
            blended_offset += weight * offset

        # Apply deadband to prevent jitter
        if abs(blended_offset) < self.offset_deadband:
            return 0.0

        return blended_offset
