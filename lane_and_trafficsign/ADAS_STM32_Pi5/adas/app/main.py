"""
Fusion Control Test Script (Lane + Sign + Dashboard)
====================================================
Chạy kết hợp nhận diện làn đường và biển báo.
Ra quyết định hợp nhất và tự động đẩy dữ liệu (POST) lên Web Dashboard.

Dữ liệu hiển thị trên Web Dashboard bao gồm:
  - TX (Pi → STM32): target_speed, steering_error, brake_command, cmd_id
  - RX (STM32 → Pi): distance_left, distance_right, actual_rpm
  - System: fusion_state, detected_signs, uart_connected
"""

import cv2 as cv
import sys
import os
import argparse
import numpy as np
from pathlib import Path

# Path setup
_APP_DIR = Path(__file__).resolve().parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

_WORKSPACE_DIR = Path(__file__).resolve().parents[4]
if str(_WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_DIR))

# ADAS Modules
from perception.lane_detector import LaneDetector
from control.lane_controller import LaneController
from perception.sign_detector import SignDetector
from control.sign_controller import SignController
from decision.fusion import FusionController
from communication.uart import UartConfiguration
from config import lane_control_config as ctrl_cfg

# Webserver Modules
from webserver.server import start_dashboard_thread
from webserver.state import update_vehicle_state
from webserver.stream import set_global_frame

_DEFAULT_VIDEO = os.path.join(_APP_DIR, "perception", "videos", "VIDEO_GOC_TESTCASE_1.mp4")


def _has_picamera():
    """Kiểm tra xem đang chạy trên Pi thật có picamera2 không."""
    try:
        import picamera2
        return True
    except ImportError:
        return False


def parse_args():
    parser = argparse.ArgumentParser(description="Fusion (Lane+Sign) test on video with Dashboard")
    parser.add_argument("--video", default=_DEFAULT_VIDEO, help="Path to input video file (default: test video)")
    parser.add_argument("--camera", action="store_true", help="Use PiCamera instead of video file")
    parser.add_argument("--port", default="/dev/ttyAMA0", help="UART port")
    parser.add_argument("--baud", type=int, default=115200, help="UART baud rate")
    parser.add_argument("--simulate", action="store_true", help="Simulation mode (no UART)")
    parser.add_argument("--no-display", action="store_true", help="Run without GUI")
    return parser.parse_args()

def main():
    args = parse_args()

    # Tự động dùng PiCamera nếu đang trên Pi thật và không chỉ định --video riêng (và không ở chế độ simulate)
    if not args.camera and not args.simulate and _has_picamera() and args.video == _DEFAULT_VIDEO:
        print("[AUTO] Phát hiện PiCamera → Tự động chuyển sang camera thật.")
        args.camera = True

    if "DISPLAY" not in os.environ and not args.no_display:
        args.no_display = True

    # 1. Start Dashboard
    print("[INFO] Khởi động Web Dashboard...")
    start_dashboard_thread()

    # 2. Open Video or Camera
    if args.camera:
        print("[INFO] Khởi động PiCamera...")
        from camera.camera import Camera
        cam = Camera()
        cap = None
    else:
        print(f"[INFO] Khởi động Video: {args.video}")
        cap = cv.VideoCapture(args.video)
        cam = None

    # 3. Setup UART
    uart = UartConfiguration(port=args.port, baudrate=args.baud)
    if args.simulate:
        uart_connected = False
        print("[MODE] Simulation (UART disabled)")
    else:
        uart_connected = uart.connect()
        if uart_connected:
            print(f"[UART] Connected on {args.port}")
        else:
            print(f"[UART] Failed on {args.port} -> Fallback to SIMULATION")

    # 4. Setup AI & Fusion
    lane_detector = LaneDetector()
    sign_detector = SignDetector()
    
    # Chia sẻ UART chung cho cả 2 Controller
    lane_ctrl = LaneController(uart=uart)
    sign_ctrl = SignController(uart=uart)
    
    fusion_ctrl = FusionController(lane_ctrl, sign_ctrl)

    # Đẩy trạng thái UART ban đầu lên Web
    update_vehicle_state(uart_connected=uart_connected)

    # 5. Main Loop
    print("[INFO] Bắt đầu quá trình nhận diện...")
    while True:
        if cam:
            frame = cam.get_frame()
            if frame is None:
                continue
        else:
            ret, frame = cap.read()
            if not ret:
                # Lặp lại video
                cap.set(cv.CAP_PROP_POS_FRAMES, 0)
                continue
        
        # A. LANE DETECTION
        annotated, lane_data = lane_detector.process_frame(frame, return_debug=True)
        left_fit = lane_data.get("left_fit")
        right_fit = lane_data.get("right_fit")
        lane_valid = lane_data.get("valid", False)
        
        height, width = frame.shape[:2]
        ploty = np.linspace(0, height - 1, height)
        center_fitx = None
        if left_fit is not None and right_fit is not None:
            left_fitx = np.polyval(left_fit, ploty)
            right_fitx = np.polyval(right_fit, ploty)
            center_fitx = (left_fitx + right_fitx) / 2

        # B. SIGN DETECTION
        detected_signs = sign_detector.find_sign(annotated, conf_thres=0.5, imgsz=320)
        
        if detected_signs:
            cv.putText(annotated, f"Signs: {', '.join(detected_signs)}", (10, 80), cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        # C. DECISION FUSION
        fusion_status = fusion_ctrl.update(detected_signs, left_fit, right_fit, center_fitx, ploty, lane_valid, frame=frame)

        # ================================================================
        # D. TRÍCH XUẤT DỮ LIỆU UART 2 CHIỀU ĐẨY LÊN WEB DASHBOARD
        # ================================================================
        state_name = fusion_status.get("state", "unknown")

        # --- Dữ liệu TX (Pi → STM32) ---
        if state_name == "lane_following" and fusion_status.get("lane_result"):
            lane_res = fusion_status["lane_result"]
            tx_speed = int(lane_res.get("speed", 0))
            tx_steering = lane_res.get("steering_angle", 0)
            tx_flags = lane_res.get("flags", 1)
            # Khắc phục xung đột ID: LaneController dùng cờ 3 (1|2) cho chệch làn, 
            # nhưng Web UI dùng ID 3 cho Biển STOP và ID 4 cho Chệch làn.
            if tx_flags == 3:
                tx_flags = 4

            # Normalize steering angle thành steering_error [-100, 100]
            tx_steering_error = int(max(-100, min(100, tx_steering / ctrl_cfg.MAX_STEERING_ANGLE * 100.0)))
            tx_brake = 1 if tx_speed == 0 else 0
            # Đọc telemetry từ lane_ctrl (đã đọc trong update())
            response = lane_res.get("response", None)
            
            status_code = tx_flags
        else:
            tx_speed = int(sign_ctrl.current_speed)
            tx_steering_error = int(max(-100, min(100, sign_ctrl.current_steering)))
            tx_flags = 3 if state_name == "stopped" else 2
            tx_brake = 1 if tx_speed == 0 else 0
            response = sign_ctrl.read_stm32_response()
            
            status_code = tx_flags

        # --- Dữ liệu RX (STM32 → Pi) ---
        rx_distance_left = response["distance_left"] if response else 999
        rx_distance_right = response["distance_right"] if response else 999
        rx_actual_rpm = response["actual_rpm"] if response else 0

        # ---- Vẽ HUD trạng thái Fusion ----
        cv.putText(annotated, f"Fusion: {state_name.upper()}", (10, 110), cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        # ---- Vẽ HUD thông tin Navigation (Dijkstra + ArUco) ----
        nav_info = fusion_status.get("nav_info")
        if nav_info:
            nav_action = nav_info.get("action", "---")
            nav_marker = nav_info.get("marker_id", "---")
            nav_goal = nav_info.get("goal", "---")
            nav_path = nav_info.get("path", [])
            cv.putText(annotated, f"NAV: {nav_action} | Marker:{nav_marker} | Goal:{nav_goal}",
                       (10, 140), cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            if nav_path:
                path_str = " > ".join(map(str, nav_path[:8]))  # Hiển thị tối đa 8 node
                cv.putText(annotated, f"Path: {path_str}",
                           (10, 165), cv.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 0), 1)

        # ---- Cập nhật Web Dashboard (đầy đủ UART 2 chiều) ----
        update_vehicle_state(
            # TX (Pi → STM32)
            cmd_id=tx_flags,
            target_speed=tx_speed,
            steering_error=tx_steering_error,
            brake_command=tx_brake,
            # RX (STM32 → Pi)
            distance_left=rx_distance_left,
            distance_right=rx_distance_right,
            actual_rpm=rx_actual_rpm,
            # System status
            status=status_code,
            fusion_state=state_name,
            detected_signs=detected_signs,
            uart_connected=uart_connected,
        )
        set_global_frame(annotated)

        # ---- Hiển thị nội bộ ----
        if not args.no_display:
            cv.imshow("Fusion Control Test", annotated)
            key = cv.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break

    if cap:
        cap.release()
    uart.close()
    cv.destroyAllWindows()
    print("[EXIT] Hoàn tất.")

if __name__ == "__main__":
    main()
