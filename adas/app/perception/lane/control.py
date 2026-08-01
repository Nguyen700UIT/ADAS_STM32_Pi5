import sys
from pathlib import Path

FILE = Path(__file__).resolve()
ROOT = FILE.parents[4] 

if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))


import cv2 as cv
import time
import numpy as np

from adas.app.config import lane_control_config as cfg
from adas.app.communication.protocol import UartProtocol
from adas.app.communication.uart import UartConfiguration


class LaneController:
    def __init__(self, port=None, baudrate=None, timeout=None, img_width=640, img_height=480, warp_matrix=None):
        # Pre-compute the car's center position in warped (bird's-eye) space
        # by transforming the image center through the perspective warp
        self.img_width = img_width
        self.img_height = img_height
        self.warp_matrix = warp_matrix
        if warp_matrix is not None:
            # The ideal lane center (setpoint) is the center of the WARP_DST rectangle.
            # We use this instead of the mapped camera center to correctly handle
            # off-center camera mounts (which make WARP_SRC asymmetric).
            from adas.app.config import lane_config
            dst_left = lane_config.WARP_DST[0][0]
            dst_right = lane_config.WARP_DST[2][0]
            self.img_center_warped = (dst_left + dst_right) / 2.0
        else:
            self.img_center_warped = cfg.IMG_CENTER

        self.lookahead_points_y = getattr(cfg, 'LOOKAHEAD_POINTS_Y', [200, 320, 380])
        self.lookahead_weights = getattr(cfg, 'LOOKAHEAD_POINTS_WEIGHTS', [0.2, 0.3, 0.5])
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

        # Khởi tạo UART với cấu hình tối ưu luồng
        self.uart = UartConfiguration(
            port=port or "/dev/ttyAMA0",
            baudrate=baudrate or 115200,
            timeout=timeout or 0.005,
        )
        self.uart_connected = self.uart.connect()

        self.smoothed_steering = 0.0            
        self.consecutive_departure = 0           
        self.frame_counter = 0                   
        self.last_send_time = time.time()        
        self.last_stm32_response = None          

    def is_connected(self) -> bool:
        return self.uart_connected and self.uart.serial_port is not None and self.uart.serial_port.is_open

    def close(self):
        self.uart.close()
        self.uart_connected = False

    def calc_offset(self, center_fitx, ploty):
        if center_fitx is None or ploty is None:
            return 0.0

        blended_offset = 0.0
        for lookahead_y, weight in zip(self.lookahead_points_y, self.lookahead_weights):
            idx = np.argmin(np.abs(ploty - lookahead_y))
            lane_center_x = center_fitx[idx]
            # Both lane_center_x and img_center_warped are in warped space
            offset = lane_center_x - self.img_center_warped
            blended_offset += weight * offset

        if abs(blended_offset) < self.offset_deadband:
            return 0.0
        return blended_offset

    def pure_pursuit_control(self, center_fitx, ploty):
        if center_fitx is None or ploty is None or len(ploty) == 0:
            return 0.0

        # Vehicle origin is assumed to be bottom center of warped image
        origin_x = self.img_center_warped
        origin_y = self.img_height

        # Lookahead distance and wheelbase from config (with defaults)
        from adas.app.config import lane_control_config as cfg
        Ld = getattr(cfg, 'LOOKAHEAD_DISTANCE_PX', 250)
        wheelbase = getattr(cfg, 'WHEELBASE_PX', 270)

        # Target y is Ld pixels ahead (y decreases going up)
        target_y = origin_y - Ld

        # Find closest point on path
        idx = np.argmin(np.abs(ploty - target_y))
        target_x = center_fitx[idx]
        actual_target_y = ploty[idx]

        dx = target_x - origin_x
        dy = origin_y - actual_target_y # positive distance forward

        Ld_sq = dx**2 + dy**2
        if Ld_sq == 0:
            return 0.0

        # Pure pursuit curvature gamma = 2 * dx / Ld^2
        gamma = 2 * dx / Ld_sq
        
        # Steering angle delta = arctan(gamma * wheelbase)
        steering_rad = np.arctan(gamma * wheelbase)
        steering_deg = float(np.degrees(steering_rad))

        return steering_deg

    def compute_curvature(self, left_fit, right_fit, ploty):
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
        if curvature <= 0 or curvature > self.straight_radius:
            return self.max_speed
        elif curvature > self.curve_radius:
            return self.normal_speed
        else:
            return self.low_speed

    def build_flags(self, offset, lane_valid):
        flags = 0
        if lane_valid:
            flags |= 1

        if lane_valid and abs(offset) > self.offset_deadband:
            if abs(offset) > cfg.DEPARTURE_THRESHOLD_PX:
                self.consecutive_departure += 1
                if self.consecutive_departure >= cfg.DEPARTURE_CONSECUTIVE_FRAMES:
                    flags |= 2
            else:
                self.consecutive_departure = 0
        else:
            self.consecutive_departure = 0

        return flags

    def smooth_steering(self, raw_steering):
        self.smoothed_steering = (
            self.steering_ema_alpha * raw_steering +
            (1.0 - self.steering_ema_alpha) * self.smoothed_steering
        )
        return self.smoothed_steering

    def send_to_stm32(self, steering_val, curvature, speed, flags, is_angle=False):
        """
        Đóng gói chuẩn xác theo _TX_STRUCT = struct.Struct('<BhbB')
        Returns True if packet was sent successfully.
        """
        # Quy đổi dữ liệu CV map sang format Control 
        cmd_id = flags if flags > 0 else 1
        target_speed = int(speed)
        
        if is_angle:
            # Normalize steering angle to [-100, 100] steering error range
            normalized = steering_val / self.max_steering_angle * 100.0
        else:
            # Normalize pixel offset to [-100, 100] steering error range
            # offset is in pixels (warped space), MAX_OFFSET_PX defines full-scale
            normalized = steering_val / cfg.MAX_OFFSET_PX * 100.0
            
        steering_error = int(max(-100, min(100, normalized)))

        # Apply EMA smoothing to prevent jerky steering
        steering_error = int(self.smooth_steering(steering_error))
        steering_error = max(-100, min(100, steering_error))
        
        brake_command = 1 if speed == 0 else 0

        packet = UartProtocol.pack_data(cmd_id, target_speed, steering_error, brake_command)
        if packet:
            success = self.uart.send_raw_bytes(packet)
            if success:
                self.last_send_time = time.time()
            return success
        return False

    def read_stm32_response(self):
        """
        Đọc chính xác 9 Bytes theo RX_PACKET_SIZE mới
        """
        raw = self.uart.read_raw_bytes(UartProtocol.RX_PACKET_SIZE)
        if raw and len(raw) == UartProtocol.RX_PACKET_SIZE:
            self.last_stm32_response = UartProtocol.unpack_data(raw)
        return self.last_stm32_response

    def update(self, left_fit, right_fit, center_fitx, ploty, lane_valid):
        self.frame_counter += 1

        offset = self.calc_offset(center_fitx, ploty)
        steering_angle = self.pure_pursuit_control(center_fitx, ploty)
        curvature = self.compute_curvature(left_fit, right_fit, ploty)
        speed = self.select_speed(curvature)

        if not lane_valid:
            speed = int(speed * 0.3)

        flags = self.build_flags(offset, lane_valid)

        # Gửi dữ liệu đồng bộ
        sent = self.send_to_stm32(steering_angle, curvature, speed, flags, is_angle=True)
        
        # Nhận dữ liệu đồng bộ
        response = self.read_stm32_response()

        return {
            "offset": offset,
            "steering_angle": steering_angle,
            "curvature": curvature,
            "speed": speed,
            "flags": flags,
            "sent": sent,
            "response": response,
        }

    def reset(self):
        self.smoothed_steering = 0.0
        self.consecutive_departure = 0
        self.last_stm32_response = None