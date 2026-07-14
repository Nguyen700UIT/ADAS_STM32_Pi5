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
        blended_offset = 0.0
        for lookahead_y, weight in zip(self.lookahead_points_y, self.lookahead_weights):
            idx = np.argmin(np.abs(ploty - lookahead_y))
            lane_center_x = center_fitx[idx]
            offset = lane_center_x - self.img_center
            blended_offset += weight * offset

        if abs(blended_offset) < self.offset_deadband:
            return 0.0
        return blended_offset

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

    def send_to_stm32(self, offset, curvature, speed, flags):
        """
        Đóng gói chuẩn xác theo _TX_STRUCT = struct.Struct('<BhbB')
        """
        # Quy đổi dữ liệu CV map sang format Control 
        cmd_id = flags if flags > 0 else 1
        target_speed = int(speed)
        
        # Giới hạn steering_error theo byte int8_t (-128 đến 127)
        steering_error = int(max(-100, min(100, offset))) 
        
        brake_command = 1 if speed == 0 else 0

        packet = UartProtocol.pack_data(cmd_id, target_speed, steering_error, brake_command)
        if packet:
            self.uart.send_raw_bytes(packet)
            self.last_send_time = time.time()

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
        curvature = self.compute_curvature(left_fit, right_fit, ploty)
        speed = self.select_speed(curvature)

        if not lane_valid:
            speed = int(speed * 0.3)

        flags = self.build_flags(offset, lane_valid)

        # Gửi dữ liệu đồng bộ
        self.send_to_stm32(offset, curvature, speed, flags)
        
        # Nhận dữ liệu đồng bộ
        response = self.read_stm32_response()

        return {
            "offset": offset,
            "curvature": curvature,
            "speed": speed,
            "flags": flags,
            "sent": True,
            "response": response,
        }

    def reset(self):
        self.smoothed_steering = 0.0
        self.consecutive_departure = 0
        self.last_stm32_response = None