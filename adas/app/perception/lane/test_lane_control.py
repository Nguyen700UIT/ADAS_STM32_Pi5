"""
Lane Control Test Script
========================
Runs lane detection on a video file, computes control signals
(offset, curvature, speed, flags), and sends them to STM32 via UART.

Usage:
    python test_lane_control.py --port COM3                # Windows
    python test_lane_control.py --port /dev/ttyAMA0        # Raspberry Pi
    python test_lane_control.py --port COM3 --video <path> # Custom video
    python test_lane_control.py --simulate                  # No UART (sim only)

Controls while running:
    q / ESC  -> Quit
    d        -> Toggle debug overlay
    SPACE    -> Pause / Resume
"""

import cv2 as cv
import sys
import os
import time
import argparse
import numpy as np
import traceback
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup – ensure we can import sibling modules
# ---------------------------------------------------------------------------
_APP_DIR = Path(__file__).resolve().parents[4]
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

from adas.app.perception.lane.detector import LaneDetector
from adas.app.config import lane_control_config as ctrl_cfg
from adas.app.communication.protocol import UartProtocol
from adas.app.communication.uart import UartConfiguration

# ---------------------------------------------------------------------------
# Default paths
# ---------------------------------------------------------------------------
_DEFAULT_VIDEO = os.path.join(os.path.dirname(__file__), "VIDEO_GOC_TESTCASE_1.mp4")
_DEFAULT_OUTPUT = os.path.join(os.path.dirname(__file__), "output_lane_control.mp4")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Lane control test on video – sends signals to STM32 via UART"
    )
    parser.add_argument("--video", default=_DEFAULT_VIDEO, help="Path to input video file")
    parser.add_argument("--output", default=_DEFAULT_OUTPUT, help="Path to save output annotated video")
    parser.add_argument("--port", default=None, help="UART port (e.g. COM3 on Windows, /dev/ttyAMA0 on Pi)")
    parser.add_argument("--baud", type=int, default=115200, help="UART baud rate (default: 115200)")
    parser.add_argument("--simulate", action="store_true", help="Simulation mode – no UART")
    parser.add_argument("--loop", action="store_true", help="Loop video when reaching the end")
    parser.add_argument("--no-display", action="store_true", help="Run without GUI (headless mode)")
    parser.add_argument("--save", action="store_true", help="Save output video to file")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# send_to_stm32 – directly from LaneController (control.py)
# ---------------------------------------------------------------------------
def send_to_stm32(uart: UartConfiguration, offset: float, speed: int, flags: int) -> bool:
    """
    Build and send a control packet to STM32 via UART.

    Packet format (TX_STRUCT = struct.Struct('<BhbB')):
      [0xAA, 0x55] + cmd_id(1B) + target_speed(2B) + steering_error(1B) + brake(1B) + checksum(1B)
    """
    cmd_id = flags if flags > 0 else 1
    target_speed = int(speed)
    # Normalize pixel offset to [-100, 100] steering error range
    normalized = offset / ctrl_cfg.MAX_OFFSET_PX * 100.0
    steering_error = int(max(-100, min(100, normalized)))
    brake_command = 1 if speed == 0 else 0

    packet = UartProtocol.pack_data(cmd_id, target_speed, steering_error, brake_command)
    if packet:
        return uart.send_raw_bytes(packet)
    return False


def read_stm32_response(uart: UartConfiguration) -> dict:
    """Read and parse a 9-byte response packet from STM32."""
    raw = uart.read_raw_bytes(UartProtocol.RX_PACKET_SIZE)
    if raw and len(raw) == UartProtocol.RX_PACKET_SIZE:
        return UartProtocol.unpack_data(raw)
    return None


# ---------------------------------------------------------------------------
# Control computation helpers (from LaneController)
# ---------------------------------------------------------------------------
def calc_offset(center_fitx, ploty, img_center_warped):
    """
    Compute blended offset from lookahead points.
    
    Both center_fitx and img_center_warped are in warped (bird's-eye) space.
    """
    if center_fitx is None or ploty is None:
        return 0.0
    blended_offset = 0.0
    for lookahead_y, weight in zip(ctrl_cfg.LOOKAHEAD_POINTS_Y, ctrl_cfg.LOOKAHEAD_POINTS_WEIGHTS):
        # Scale lookahead points from 480p to current resolution
        scaled_lookahead = int(lookahead_y * (ploty[-1] / 480.0)) if ploty[-1] > 480 else lookahead_y
        idx = np.argmin(np.abs(ploty - scaled_lookahead))
        lane_center_x = center_fitx[idx]
        offset = lane_center_x - img_center_warped
        blended_offset += weight * offset
    if abs(blended_offset) < ctrl_cfg.OFFSET_DEADBAND:
        return 0.0
    return blended_offset


def compute_curvature(left_fit, right_fit, ploty):
    """Compute average road curvature radius."""
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
            curvatures.append(ctrl_cfg.STRAIGHT_RADIUS)
        else:
            R = (1 + (2 * a * y_eval + b) ** 2) ** 1.5 / denom
            curvatures.append(R)
    return float(np.mean(curvatures)) if curvatures else 0.0


def select_speed(curvature):
    """Select speed based on curvature."""
    if curvature <= 0 or curvature > ctrl_cfg.STRAIGHT_RADIUS:
        return ctrl_cfg.MAX_SPEED
    elif curvature > ctrl_cfg.CURVE_RADIUS:
        return ctrl_cfg.NORMAL_SPEED
    else:
        return ctrl_cfg.LOW_SPEED


def build_flags(offset, lane_valid, consecutive_departure):
    """Build flags: bit0=lane_valid, bit1=departure_warning."""
    flags = 0
    if lane_valid:
        flags |= 1
    if lane_valid and abs(offset) > ctrl_cfg.OFFSET_DEADBAND:
        if abs(offset) > ctrl_cfg.DEPARTURE_THRESHOLD_PX:
            consecutive_departure += 1
            if consecutive_departure >= ctrl_cfg.DEPARTURE_CONSECUTIVE_FRAMES:
                flags |= 2
        else:
            consecutive_departure = 0
    else:
        consecutive_departure = 0
    return flags, consecutive_departure


def format_control_info(offset, curvature, speed, flags) -> str:
    curve_label = (
        "STRAIGHT" if curvature > ctrl_cfg.STRAIGHT_RADIUS
        else "CURVE" if curvature > ctrl_cfg.CURVE_RADIUS
        else "SHARP"
    )
    warn = ""
    if flags & 2:
        warn = " [DEPARTURE]"
    elif not (flags & 1):
        warn = " [NO LANE]"
    return (f"Offset:{offset:+7.1f}px  Curv:{curvature:>6.0f}m  "
            f"({curve_label:>8s})  Speed:{speed:>2d}  Flags:{flags:>2d}{warn}")


def draw_control_overlay(frame, offset, curvature, speed, flags, frame_idx, uart_connected, stm32_response):
    h, w = frame.shape[:2]
    overlay = frame.copy()
    bar_h = 80
    cv.rectangle(overlay, (0, 0), (w, bar_h), (0, 0, 0), -1)
    cv.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

    mode_str = "UART TX" if uart_connected else "SIMULATION"
    mode_color = (0, 255, 0) if uart_connected else (0, 255, 255)
    cv.putText(frame, mode_str, (w - 220, 30), cv.FONT_HERSHEY_SIMPLEX, 0.65, mode_color, 2)
    cv.putText(frame, f"Frame: {frame_idx}", (10, 25), cv.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)

    info = format_control_info(offset, curvature, speed, flags)
    cv.putText(frame, info, (10, 55), cv.FONT_HERSHEY_SIMPLEX, 0.55, (180, 230, 255), 2)

    # Offset bar
    bar_y = bar_h + 10
    bar_center_x = w // 2
    bar_width = 300
    bar_left = bar_center_x - bar_width // 2
    cv.rectangle(frame, (bar_left, bar_y), (bar_left + bar_width, bar_y + 8), (60, 60, 60), -1)
    cv.line(frame, (bar_center_x, bar_y - 2), (bar_center_x, bar_y + 10), (255, 255, 255), 2)
    if abs(offset) > ctrl_cfg.OFFSET_DEADBAND:
        disp_offset = np.clip(offset, -bar_width // 2, bar_width // 2)
        ind_x = int(bar_center_x + disp_offset)
        ind_color = (0, 0, 255) if abs(offset) > ctrl_cfg.DEPARTURE_THRESHOLD_PX else (0, 255, 255)
        cv.circle(frame, (ind_x, bar_y + 4), 6, ind_color, -1)
        cv.circle(frame, (ind_x, bar_y + 4), 6, (255, 255, 255), 1)

    # Warnings
    if flags & 2:
        cv.putText(frame, "!!! LANE DEPARTURE !!!", (w // 2 - 200, h - 20),
                   cv.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
    elif not (flags & 1):
        cv.putText(frame, "Lane not detected", (w // 2 - 150, h - 20),
                   cv.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)

    # STM32 response
    legend_y = h - 60
    if uart_connected:
        if stm32_response:
            rx_str = (f"STM32 RX  L:{stm32_response['distance_left']:>4.0f}  "
                      f"R:{stm32_response['distance_right']:>4.0f}  "
                      f"RPM:{stm32_response['actual_rpm']:>+5.0f}")
            cv.putText(frame, rx_str, (10, legend_y), cv.FONT_HERSHEY_SIMPLEX, 0.5, (100, 255, 100), 1)
        else:
            cv.putText(frame, "Waiting for STM32 response...", (10, legend_y),
                       cv.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)
    else:
        cv.putText(frame, "[SIMULATED] No data sent to STM32", (10, legend_y),
                   cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    return frame


def main():
    args = parse_args()
    if "DISPLAY" not in os.environ and not args.no_display:
        print("[INFO] No DISPLAY environment variable found. Forcing --no-display mode.")
        args.no_display = True

    # ------------------------------------------------------------------
    # Open video
    # ------------------------------------------------------------------
    video_path = args.video
    if not os.path.isfile(video_path):
        print(f"[ERROR] Video not found: {video_path}")
        fallback = os.path.join(os.path.dirname(__file__), "test_video.mp4")
        if os.path.isfile(fallback):
            print(f"[INFO]  Falling back to: {fallback}")
            video_path = fallback
        else:
            print("[ERROR] No valid video file found.")
            sys.exit(1)

    cap = cv.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[ERROR] Could not open video: {video_path}")
        sys.exit(1)

    fps = cap.get(cv.CAP_PROP_FPS)
    width = int(cap.get(cv.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv.CAP_PROP_FRAME_COUNT))

    print(f"\n{'=' * 60}")
    print(f"  Video:    {os.path.basename(video_path)}")
    print(f"  Size:     {width}x{height}")
    print(f"  FPS:      {fps:.2f}")
    print(f"  Frames:   {total_frames}")
    if args.loop:
        print(f"  Loop:     ON")
    if args.no_display:
        print(f"  Display:  OFF")
    print(f"{'=' * 60}\n")

    # ------------------------------------------------------------------
    # Initialise UART
    # ------------------------------------------------------------------
    uart = UartConfiguration(
        port=args.port or "/dev/ttyAMA0",
        baudrate=args.baud,
        timeout=0.005,
    )
    uart_connected = uart.connect()

    if args.simulate:
        print("[MODE] Simulation mode (UART disabled)")
        uart_connected = False
    elif uart_connected:
        print(f"[UART] Connected on {uart.port} @ {uart.baudrate} baud")
    else:
        print(f"[UART] Failed to connect on {uart.port}")
        print("[UART] Falling back to simulation mode")
        uart_connected = False

    # ------------------------------------------------------------------
    # Initialise detector & compute warped car center
    # ------------------------------------------------------------------
    detector = LaneDetector()

    # Transform the image center (width/2, height-1) into warped
    # (bird's-eye) space. The lane polynomials (left_fitx, right_fitx,
    # center_fitx) are all in warped coordinates, so the offset must be
    # computed relative to the car's position in warped space.
    warp_matrix, _ = detector._get_warp_matrices(width, height)
    # Use the bottom edge of the source trapezoid to avoid extrapolation out of bounds
    try:
        from adas.app.perception.lane import lane_config
        bottom_src_y = lane_config.WARP_SRC[0][1]
        scale_y = (height - 1) / (lane_config.IMAGE_HEIGHT - 1)
        car_y = bottom_src_y * scale_y
    except:
        car_y = height - 1
        
    car_pt = np.float32([[[width / 2, car_y]]])
    car_warped = cv.perspectiveTransform(car_pt, warp_matrix)
    img_center_warped = car_warped[0, 0, 0]
    print(f"[INFO]  Image center ({width/2}, {height-1}) → warped x = {img_center_warped:.1f}")

    # ------------------------------------------------------------------
    # Video writer
    # ------------------------------------------------------------------
    out = None
    if args.save:
        fourcc = cv.VideoWriter_fourcc(*"mp4v")
        out = cv.VideoWriter(args.output, fourcc, fps, (width, height))
        print(f"[OUTPUT] Saving to: {args.output}")

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------
    frame_count = 0
    failed_count = 0
    tx_count = 0
    rx_count = 0
    consecutive_departure = 0
    last_stm32_response = None
    start_time = time.time()
    paused = False
    show_debug = True

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    while True:
        if not paused:
            ret, frame = cap.read()
            if not ret:
                if args.loop:
                    cap.set(cv.CAP_PROP_POS_FRAMES, 0)
                    frame_count = 0
                    print("[LOOP] Restarting video...")
                    continue
                else:
                    break
            frame_count += 1

        # ---- Lane detection ----
        try:
            annotated, data = detector.process_frame(frame, return_debug=True)
        except Exception as e:
            print(f"  [WARN] Frame {frame_count}: {e}")
            traceback.print_exc()
            failed_count += 1
            annotated = frame.copy()
            data = {"left_fit": None, "right_fit": None, "valid": False, "binary": np.zeros((height, width), dtype=np.uint8), "sliding_windows": np.zeros((height, width, 3), dtype=np.uint8)}

        # ---- Extract lane fits ----
        left_fit = data.get("left_fit")
        right_fit = data.get("right_fit")
        lane_valid = data.get("valid", False)
        center_fitx = None
        ploty = np.linspace(0, height - 1, height)

        if left_fit is not None and right_fit is not None:
            left_fitx = np.polyval(left_fit, ploty)
            right_fitx = np.polyval(right_fit, ploty)
            center_fitx = (left_fitx + right_fitx) / 2

        # ---- Compute control signals ----
        offset = calc_offset(center_fitx, ploty, img_center_warped)
        curvature = compute_curvature(left_fit, right_fit, ploty)
        speed = select_speed(curvature)
        if not lane_valid:
            speed = int(speed * 0.3)
        flags, consecutive_departure = build_flags(offset, lane_valid, consecutive_departure)

        # ---- Send to STM32 ----
        sent = False
        if uart_connected:
            sent = send_to_stm32(uart, offset, speed, flags)
            if sent:
                tx_count += 1
            # Read response
            last_stm32_response = read_stm32_response(uart)
            if last_stm32_response:
                rx_count += 1
        else:
            last_stm32_response = None

        # ---- Console logging ----
        if frame_count % max(1, int(fps / 2)) == 0 or not lane_valid or (flags & 2):
            ctrl_line = format_control_info(offset, curvature, speed, flags)
            if uart_connected:
                status = "[TX-OK]" if sent else "[TX-FAIL]"
                # Build hex for display
                cmd_id = flags if flags > 0 else 1
                normalized_log = offset / ctrl_cfg.MAX_OFFSET_PX * 100.0
                steering_error = int(max(-100, min(100, normalized_log)))
                brake = 1 if speed == 0 else 0
                pkt = UartProtocol.pack_data(cmd_id, int(speed), steering_error, brake)
                hex_str = " ".join(f"{b:02X}" for b in pkt) if pkt else "N/A"
                
                rx_info = ""
                if last_stm32_response:
                    rx_info = f"  |  RX L:{last_stm32_response['distance_left']}cm R:{last_stm32_response['distance_right']}cm RPM:{last_stm32_response['actual_rpm']}"
                else:
                    rx_info = "  |  RX: None"
                    
                print(f"  [{frame_count:>5d}/{total_frames}]  {ctrl_line}  {status}  TX:{hex_str}{rx_info}")
            else:
                print(f"  [{frame_count:>5d}/{total_frames}]  {ctrl_line}  [SIM]")

        # ---- Draw HUD ----
        if show_debug:
            annotated = draw_control_overlay(annotated, offset, curvature, speed, flags,
                                             frame_count, uart_connected, last_stm32_response)

        # ---- Save ----
        if out is not None:
            out.write(annotated)

        # ---- Display ----
        if not args.no_display:
            cv.imshow("Lane Control Test", annotated)
            if show_debug:
                binary_view = data.get("binary", np.zeros((height, width), dtype=np.uint8))
                if len(binary_view.shape) == 2:
                    binary_view = cv.cvtColor(binary_view, cv.COLOR_GRAY2BGR)
                sliding_view = data.get("sliding_windows", np.zeros((height, width, 3), dtype=np.uint8))
                combo = np.hstack((cv.resize(binary_view, (width // 2, height // 2)),
                                   cv.resize(sliding_view, (width // 2, height // 2))))
                cv.imshow("Debug - Binary | Sliding Windows", combo)

        # ---- Keys ----
        key = cv.waitKey(1) & 0xFF if not args.no_display else -1
        if key in (ord("q"), 27):
            print("  Quit requested.")
            break
        elif key == ord("d"):
            show_debug = not show_debug
            print(f"[TOGGLE] Debug overlay: {'ON' if show_debug else 'OFF'}")
        elif key == ord(" "):
            paused = not paused
            print(f"{'[PAUSED]' if paused else '[RESUMED]'}")

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------
    cap.release()
    if out is not None:
        out.release()
    uart.close()
    cv.destroyAllWindows()

    elapsed = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"  RESULT SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Processed:    {frame_count} / {total_frames} frames")
    print(f"  Failed:       {failed_count}")
    print(f"  TX sent:      {tx_count}")
    print(f"  RX received:  {rx_count}")
    print(f"  Elapsed:      {elapsed:.2f} s")
    print(f"  FPS:          {frame_count / max(elapsed, 0.001):.2f}")
    print(f"  Mode:         {'UART' if uart_connected else 'SIMULATION'}")
    print(f"{'=' * 60}")
    print("  Test complete.")


if __name__ == "__main__":
    main()
