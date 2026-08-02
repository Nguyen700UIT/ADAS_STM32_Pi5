from threading import Lock
from time import time

STATUS_LABELS = {
    0: "Mất vạch kẻ đường",
    1: "Đang giữ làn",
    3: "Cảnh báo chệch làn!",
}

state_lock = Lock()
vehicle_state = {
    "speed": 0.0,
    "status": 0,
    "angle": 0.0,
    "distance_left": 999,
    "distance_right": 999,
    "actual_rpm": 0,
    "brake_command": 0,
    "updated_at": time(),
}


def get_public_state():
    with state_lock:
        state = dict(vehicle_state)

    status = int(state.get("status", 0))
    state["status_text"] = STATUS_LABELS.get(status, "Không xác định")
    return state


def update_vehicle_state(speed=None, status=None, angle=None, distance_left=None, distance_right=None, actual_rpm=None, brake_command=None):
    with state_lock:
        if speed is not None:
            vehicle_state["speed"] = float(speed)
        if status is not None:
            vehicle_state["status"] = int(status)
        if angle is not None:
            vehicle_state["angle"] = float(angle)
        if distance_left is not None:
            vehicle_state["distance_left"] = int(distance_left)
        if distance_right is not None:
            vehicle_state["distance_right"] = int(distance_right)
        if actual_rpm is not None:
            vehicle_state["actual_rpm"] = int(actual_rpm)
        if brake_command is not None:
            vehicle_state["brake_command"] = int(brake_command)
        vehicle_state["updated_at"] = time()
