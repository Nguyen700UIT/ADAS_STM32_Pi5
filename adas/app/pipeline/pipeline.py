from app.communication.uart import UartConfiguration
from app.communication.protocol import UartProtocol
from app.perception.lane.detector import LaneDetector
from app.perception.lane.control import LaneController
import cv2 as cv

# Khởi tạo pipeline components
detector = LaneDetector()
controller = LaneController()

def process(frame):
    """Xử lý frame, tính toán điều khiển, gửi lệnh UART và nhận phản hồi."""
    if frame is None:
        return (frame, {})

    # 1. Nhận diện làn đường
    processed_frame, left_fit, right_fit, center_fitx, ploty, lane_valid = detector.process_frame(frame)
    
    # 2. Tính toán điều khiển & Giao tiếp UART
    control_result = controller.update(left_fit, right_fit, center_fitx, ploty, lane_valid)
    
    # 3. Tổng hợp dữ liệu trả về cho Web Server
    data = {
        "target_speed": control_result.get("speed", 0),
        "steering_error": control_result.get("offset", 0),  # Hiển thị offset dưới dạng góc
        "flags": control_result.get("flags", 0),
        "brake_command": 1 if control_result.get("speed", 0) == 0 else 0,
    }
    
    # Lấy dữ liệu phản hồi từ STM32 (từ UartProtocol unpack)
    response = control_result.get("response")
    if response:
        data["distance_left"] = response.get("distance_left", 999)
        data["distance_right"] = response.get("distance_right", 999)
        data["actual_rpm"] = response.get("actual_rpm", 0)

    # Convert steering offset to angle equivalent (roughly mapped) for display
    # Controller internal uses MAX_OFFSET_PX for normalization
    from app.config import lane_control_config as ctrl_cfg
    if "steering_error" in data:
        normalized = data["steering_error"] / ctrl_cfg.MAX_OFFSET_PX * 100.0
        data["steering_error"] = max(-100, min(100, normalized))

    return (processed_frame, data)

