from threading import Lock
from time import time

STATUS_LABELS = {
    0: "Mất vạch kẻ đường",
    1: "Đang giữ làn",
    2: "Đang chuyển hướng (Biển báo)",
    3: "Dừng xe (Biển STOP)!",
    4: "Cảnh báo chệch làn!",
}

state_lock = Lock()
vehicle_state = {
    # ---- TX: Lệnh điều khiển từ Pi gửi xuống STM32 (8 bytes) ----
    # Theo protocol: [0xAA][0x55][cmd_id][target_speed_L][target_speed_H][steering_error][brake_command][checksum]
    "cmd_id": 0,
    "target_speed": 0,          # int16: Vận tốc mục tiêu (RPM)
    "steering_error": 0,        # int8: Góc lái [-100, 100]
    "brake_command": 0,         # uint8: 0=Chạy, 1=Phanh khẩn cấp

    # ---- RX: Telemetry từ STM32 báo cáo lên Pi (9 bytes) ----
    # Theo protocol: [0xAA][0x55][dist_L_L][dist_L_H][dist_R_L][dist_R_H][rpm_L][rpm_H][checksum]
    "distance_left": 999,       # uint16: Siêu âm Trái (cm), 999=Lỗi/Ngoài khoảng
    "distance_right": 999,      # uint16: Siêu âm Phải (cm), 999=Lỗi/Ngoài khoảng
    "actual_rpm": 0,            # int16: Vận tốc thực tế (Encoder)

    # ---- Trạng thái hệ thống ----
    "status": 0,                # Cờ trạng thái (flags) từ LaneController
    "fusion_state": "idle",     # Trạng thái Fusion: lane_following, turning_left, turning_right, stopped
    "detected_signs": [],       # Danh sách biển báo đang phát hiện
    "uart_connected": False,    # Trạng thái kết nối UART với STM32

    "updated_at": time(),
}


def get_public_state():
    with state_lock:
        state = dict(vehicle_state)
        # Deep copy list to avoid race condition
        state["detected_signs"] = list(vehicle_state["detected_signs"])

    status = int(state.get("status", 0))
    state["status_text"] = STATUS_LABELS.get(status, "Không xác định")
    return state


def update_vehicle_state(
    # TX fields (Pi → STM32)
    cmd_id=None,
    target_speed=None,
    steering_error=None,
    brake_command=None,
    # RX fields (STM32 → Pi)
    distance_left=None,
    distance_right=None,
    actual_rpm=None,
    # System status
    status=None,
    fusion_state=None,
    detected_signs=None,
    uart_connected=None,
    # Legacy aliases (backward compatibility with old callers)
    speed=None,
    angle=None,
):
    with state_lock:
        # TX fields
        if cmd_id is not None:
            vehicle_state["cmd_id"] = int(cmd_id)
        if target_speed is not None:
            vehicle_state["target_speed"] = int(target_speed)
        elif speed is not None:
            vehicle_state["target_speed"] = int(speed)
        if steering_error is not None:
            vehicle_state["steering_error"] = int(steering_error)
        elif angle is not None:
            vehicle_state["steering_error"] = int(angle)
        if brake_command is not None:
            vehicle_state["brake_command"] = int(brake_command)

        # RX fields
        if distance_left is not None:
            vehicle_state["distance_left"] = int(distance_left)
        if distance_right is not None:
            vehicle_state["distance_right"] = int(distance_right)
        if actual_rpm is not None:
            vehicle_state["actual_rpm"] = int(actual_rpm)

        # System status
        if status is not None:
            vehicle_state["status"] = int(status)
        if fusion_state is not None:
            vehicle_state["fusion_state"] = str(fusion_state)
        if detected_signs is not None:
            vehicle_state["detected_signs"] = list(detected_signs)
        if uart_connected is not None:
            vehicle_state["uart_connected"] = bool(uart_connected)

        vehicle_state["updated_at"] = time()
