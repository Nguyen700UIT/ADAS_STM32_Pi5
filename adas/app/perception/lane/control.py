

import time
import struct
import numpy as np

import sys
from pathlib import Path
app_dir = Path(__file__).resolve().parents[2]
sys.path.append(str(app_dir))
from config import lane_control_config as cfg


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
        self.frame_counter = 0                   # Counter for transmission rate
        self.last_send_time = time.time()        # For rate limiting

    def is_connected(self) -> bool:
        return self.uart_connected and self.uart.serial_port is not None and self.uart.serial_port.is_open

    def close(self):
        self.uart.close()
        self.uart_connected = False

    def calc_offset(self, center_fitx, ploty):
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


    def compute_curvature(self, left_fit, right_fit, ploty):
        """
        Estimate road curvature radius from lane polynomial fits.

        Computes curvature at the bottom of the image (vehicle position)
        and returns the average of left and right lane curvatures.

        Formula (for x = ay² + by + c):
            R = (1 + (2*a*y + b)²)^1.5  /  |2*a|

        Args:
            left_fit: Left lane polynomial coeffs or None.
            right_fit: Right lane polynomial coeffs or None.
            ploty: y-coordinates array.

        Returns:
            Radius of curvature in meters. Returns 0 if lanes not detected.
        """
        if left_fit is None or right_fit is None:
            return 0.0

        y_eval = ploty[-1]
        curvatures = []

        for fit in [left_fit, right_fit]:
            if fit is None or len(fit) < 2:
                continue
            a, b = fit[0], fit[1]
            denom = abs(2.0 * a)
            if denom < 1e-6:
                curvatures.append(self.straight_radius)
            else:
                R = (1 + (2 * a * y_eval + b) ** 2) ** 1.5 / denom
                curvatures.append(R)

        return float(np.mean(curvatures)) if curvatures else 0.0

    def select_speed(self, curvature):
        """
        Select speed command based on road curvature.

        Args:
            curvature: Radius of curvature in meters (0 = straight).

        Returns:
            Speed command (0-100 % PWM duty cycle).
        """
        if curvature <= 0 or curvature > self.straight_radius:
            return self.max_speed
        elif curvature > self.curve_radius:
            return self.normal_speed
        else:
            return self.low_speed

    # ======================================================================
    # SMOOTHING
    # ======================================================================

    def smooth_steering(self, raw_steering):
        """
        Apply EMA smoothing to the steering angle.

        Args:
            raw_steering: Raw computed steering angle.

        Returns:
            Smoothed steering angle.
        """
        self.smoothed_steering = (
            self.steering_ema_alpha * raw_steering +
            (1.0 - self.steering_ema_alpha) * self.smoothed_steering
        )
        return self.smoothed_steering

    # ======================================================================
    # UART SEND (8-byte packet)
    # ======================================================================

    def send_to_stm32(self, offset, speed, brake=False):
        """
        Build and send the 8-byte packet to STM32.

        The offset is smoothed via EMA before packing to reduce jitter.

        Byte layout:
            [0]     = 0xAA          (fixed header)
            [1]     = 0x55          (fixed header)
            [2]     = cmd_id        (1 = lane control)
            [3-4]   = target_speed  (int16, little-endian, -3599..3599)
            [5]     = steering_error (int8, -100..100)  smoothed via EMA
            [6]     = brake_command  (1 = emergency brake, 0 = normal)
            [7]     = checksum      (XOR of bytes 0-6)

        Args:
            offset: Lateral offset in pixels (steering_error, clamped -100..100).
            speed:  Target speed command (-3599..3599).
            brake:  Emergency brake flag.
        """
        # Apply EMA smoothing to the steering error
        smoothed_offset = self.smooth_steering(offset)

        header = bytes([0xAA, 0x55])
        cmd = bytes([1])  # cmd_id = 1 for lane control
        speed_bytes = struct.pack('<h', int(np.clip(speed, -3599, 3599)))
        steer_byte = bytes([int(np.clip(smoothed_offset, -100.0, 100.0)) & 0xFF])
        brake_byte = bytes([1 if brake else 0])

        payload = header + cmd + speed_bytes + steer_byte + brake_byte
        checksum = UartProtocol._calculate_checksum(payload)
        packet = payload + bytes([checksum])

        self.uart.send_raw_bytes(packet)
        self.last_send_time = time.time()

    # ======================================================================
    # MAIN UPDATE
    # ======================================================================

    def update(self, left_fit, right_fit, center_fitx, ploty, lane_valid):
        """
        Run the full lane control pipeline for one frame.

        Flow:
            offset = calc_offset()
            speed = select_speed(compute_curvature())
            send_to_stm32(offset, speed, brake=not lane_valid)

        Args:
            left_fit: Left lane polynomial coeffs or None.
            right_fit: Right lane polynomial coeffs or None.
            center_fitx: Lane center x-positions.
            ploty: y-coordinates corresponding to center_fitx.
            lane_valid: Whether lanes were detected.

        Returns:
            Dict with keys: offset, speed, sent.
        """
        self.frame_counter += 1

        offset = self.calc_offset(center_fitx, ploty)
        curvature = self.compute_curvature(left_fit, right_fit, ploty)
        speed = self.select_speed(curvature)

        if not lane_valid:
            speed = int(speed * 0.3)

        self.send_to_stm32(offset, speed, brake=not lane_valid)

        return {
            "offset": offset,
            "speed": speed,
            "sent": True,
        }


    def reset(self):
        """Reset all internal state (smoothing, counters, etc.)."""
        self.smoothed_steering = 0.0


