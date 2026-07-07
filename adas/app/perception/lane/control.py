

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

    