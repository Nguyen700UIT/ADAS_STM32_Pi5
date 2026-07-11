"""
Chạy test LANE DETECTION + CONTROL và in debug
Gồm: offset, curvature, speed, flags, steering angle, hướng lái

Usage:
    python test_control_debug.py                          # Chạy cả 2 test case
    python test_control_debug.py --testcase 1             # Chạy test case 1
    python test_control_debug.py --testcase 2             # Chạy test case 2
    python test_control_debug.py --no-display             # Không hiển thị
    python test_control_debug.py --interval 1             # In từng frame
"""

import cv2 as cv
import numpy as np
import os
import sys
import time
import argparse

# Import
sys.path.insert(0, os.path.dirname(__file__))
from detector import LaneDetector
import lane_control_config as cfg

# ─── Đường dẫn ───────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_VIDEOS = {
    1: {"path": os.path.join(SCRIPT_DIR, "VIDEO_GOC_TESTCASE_1.mp4"),
        "name": "TEST 1 - Duong cong"},
    2: {"path": os.path.join(SCRIPT_DIR, "test_video.mp4"),
        "name": "TEST 2 - Duong thang"},
}


def tinh_steering_angle(offset_px):
    """
    Tính góc lái từ offset.
    Công thức: angle = -STEERING_GAIN * offset
    Âm = lái trái, Dương = lái phải
    """
    goc = -cfg.STEERING_GAIN * offset_px
    goc = np.clip(goc, -cfg.MAX_STEERING_ANGLE, cfg.MAX_STEERING_ANGLE)
    return goc


def hien_thi_huong(goc):
    """Trả về ký hiệu hướng lái."""
    if abs(goc) < 1.0:
        return "DI THANG"
    elif goc < 0:
        return "<<< LAI TRAI"
    else:
        return ">>> LAI PHAI"


def in_header():
    """In tiêu đề bảng debug."""
    print("-" * 110)
    print(f"  {'Frame':>6s} | {'Lane':4s} | {'Offset(px)':>10s} | "
          f"{'Rong(px)':>8s} | {'Cong(m)':>8s} | {'Dang':>8s} | "
          f"{'Speed':>5s} | {'Flags':>5s} | {'Goc Lai':>7s} | {'Huong':>15s}")
    print("-" * 110)


def in_debug(frame_idx, total, offset, lane_width, curvature, speed, flags,
             steering_angle, valid, fps):
    """In 1 dòng debug."""
    status = "OK" if valid else "NO"
    
    # Mô tả độ cong
    if curvature <= 0 or curvature > cfg.STRAIGHT_RADIUS:
        road_type = "THANG"
    elif curvature > cfg.CURVE_RADIUS:
        road_type = "CONG-NHE"
    else:
        road_type = "CONG-GAP"
    
    # Mô tả tốc độ
    if speed >= cfg.MAX_SPEED:
        speed_desc = "MAX"
    elif speed >= cfg.NORMAL_SPEED:
        speed_desc = "TB"
    else:
        speed_desc = "CHAM"
    
    huong = hien_thi_huong(steering_angle)
    
    print(f"  [{frame_idx:6d}/{total:<6d}] "
          f"{status:4s} "
          f"{offset:>+10.1f} "
          f"{lane_width:>8.1f} "
          f"{curvature:>8.0f}({road_type:8s}) "
          f"{speed:3d}%({speed_desc:4s}) "
          f"0x{flags:02x} "
          f"{steering_angle:>+7.1f} "
          f"{huong:>15s}"
          f"  [{fps:5.1f}FPS]")


def kiem_tra_laidung(offset, steering, valid):
    """
    Kiểm tra góc lái có đúng hướng không?
    Nếu offset dương (lệch phải) → phải lái trái (steering âm) → ĐÚNG
    Nếu offset âm (lệch trái) → phải lái phải (steering dương) → ĐÚNG
    """
    if not valid or abs(steering) < 1.0:
        return True  # Bỏ qua nếu đi thẳng
    if (offset > 5 and steering < 0) or (offset < -5 and steering > 0):
        return True   # Đúng
    return False      # Sai


def chay_test(testcase_id, show_display=True, debug_interval=10):
    """Chạy test lane control trên 1 video."""
    
    if testcase_id not in TEST_VIDEOS:
        print(f"Khong tim thay test case {testcase_id}")
        return
    
    info = TEST_VIDEOS[testcase_id]
    video_path = info["path"]
    label = info["name"]
    
    if not os.path.isfile(video_path):
        print(f"[LOI] Khong tim thay video: {video_path}")
        return
    
    # Mở video
    cap = cv.VideoCapture(video_path)
    fps_src = cap.get(cv.CAP_PROP_FPS)
    width = int(cap.get(cv.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv.CAP_PROP_FRAME_COUNT))
    
    print(f"\n{'='*70}")
    print(f"  {label}")
    print(f"  File: {os.path.basename(video_path)}")
    print(f"  Size: {width}x{height}, FPS: {fps_src:.1f}, Frames: {total_frames}")
    print(f"{'='*70}")
    
    # Khởi tạo detector
    detector = LaneDetector()
    
    # Thống kê
    frame_count = 0
    valid_count = 0
    sai_lai_count = 0
    offset_sum = 0
    steering_sum = 0
    
    in_header()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        
        # Phát hiện lane
        annotated, data = detector.process_frame(frame, return_debug=True)
        
        left_fit = data["left_fit"]
        right_fit = data["right_fit"]
        valid = data["valid"]
        
        if left_fit is not None and right_fit is not None:
            # Tính center line
            h = data["binary"].shape[0]
            ploty = np.linspace(0, h - 1, h)
            left_fitx = np.polyval(left_fit, ploty)
            right_fitx = np.polyval(right_fit, ploty)
            center_fitx = (left_fitx + right_fitx) / 2
            
            # Tính offset (giống control.py)
            offset = 0.0
            for y_target, weight in zip(cfg.LOOKAHEAD_POINTS_Y, cfg.LOOKAHEAD_POINTS_WEIGHTS):
                idx = np.argmin(np.abs(ploty - y_target))
                offset += weight * (center_fitx[idx] - cfg.IMG_CENTER)
            if abs(offset) < cfg.OFFSET_DEADBAND:
                offset = 0.0
            
            # Tính độ cong
            y_eval = ploty[-1]
            curvatures = []
            for fit in [left_fit, right_fit]:
                if fit is not None and len(fit) >= 2:
                    a, b = fit[0], fit[1]
                    denom = abs(2.0 * a)
                    if denom < 1e-6:
                        curvatures.append(cfg.STRAIGHT_RADIUS)
                    else:
                        R = (1 + (2 * a * y_eval + b) ** 2) ** 1.5 / denom
                        curvatures.append(R)
            curvature = float(np.mean(curvatures)) if curvatures else 0.0
            
            # Tính tốc độ
            if curvature <= 0 or curvature > cfg.STRAIGHT_RADIUS:
                speed = cfg.MAX_SPEED
            elif curvature > cfg.CURVE_RADIUS:
                speed = cfg.NORMAL_SPEED
            else:
                speed = cfg.LOW_SPEED
            
            # Tạo flags
            flags = 0
            if valid:
                flags |= 1
            if valid and abs(offset) > cfg.DEPARTURE_THRESHOLD_PX:
                flags |= 2
            
            # Tính góc lái
            steering_angle = tinh_steering_angle(offset)
            
            # Bề rộng lane
            y_bottom = h - 1
            left_x_bottom = float(np.polyval(left_fit, y_bottom))
            right_x_bottom = float(np.polyval(right_fit, y_bottom))
            lane_width = right_x_bottom - left_x_bottom
            
            # Kiểm tra lái đúng?
            lai_dung = kiem_tra_laidung(offset, steering_angle, valid)
            if not lai_dung:
                sai_lai_count += 1
                print(f"  *** CANH BAO: Goc lai SAI huong! Offset={offset:+.1f}px, Goc={steering_angle:+.1f} ***")
            
            # In debug
            if frame_count % debug_interval == 0 or frame_count == 1:
                in_debug(frame_count, total_frames, offset, lane_width,
                        curvature, speed, flags, steering_angle, valid, fps_src)
            
            # Cập nhật thống kê
            if valid:
                valid_count += 1
                offset_sum += offset
                steering_sum += steering_angle
        else:
            # Không thấy lane
            speed = int(cfg.MAX_SPEED * 0.3)
            flags = 0
            offset = 0
            steering_angle = 0
            curvature = 0
            lane_width = 0
            
            if frame_count % debug_interval == 0:
                in_debug(frame_count, total_frames, 0, 0, 0, speed,
                        0, 0, False, fps_src)
        
        # Vẽ thông tin lên frame
        cv.putText(annotated,
                   f"Steer:{steering_angle:+.1f}deg {hien_thi_huong(steering_angle)}",
                   (50, 150), cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv.putText(annotated,
                   f"Offset:{offset:+.1f}px Curve:{curvature:.0f}m Speed:{speed}% Flags:0x{flags:02x}",
                   (50, 180), cv.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)
        
        if show_display:
            cv.imshow(f"Lane Control - {label}", annotated)
            if cv.waitKey(1) & 0xFF == ord('q'):
                print("  Nguoi dung yeu cau thoat.")
                break
    
    cap.release()
    cv.destroyAllWindows()
    
    # Tổng kết
    print(f"\n{'='*70}")
    print(f"  TONG KET - {label}")
    print(f"{'='*70}")
    print(f"  Tong frame         : {frame_count}")
    print(f"  Phat hien lane OK  : {valid_count}/{frame_count} ({100*valid_count/max(frame_count,1):.1f}%)")
    print(f"  So lan lai SAI     : {sai_lai_count}")
    
    if valid_count > 0:
        avg_off = offset_sum / valid_count
        avg_steer = steering_sum / valid_count
        print(f"  Offset trung binh  : {avg_off:+.1f} px")
        print(f"  Goc lai trung binh : {avg_steer:+.1f} deg")
        if avg_steer < -1:
            print(f"  >> Thien ve lai TRAI ({avg_steer:+.1f}°)")
        elif avg_steer > 1:
            print(f"  >> Thien ve lai PHAI ({avg_steer:+.1f}°)")
        else:
            print(f"  >> Gan nhu DI THANG")
    
    print(f"{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(description="Test Lane Detection + Control Debug")
    parser.add_argument("--testcase", "-t", type=int, default=0,
                       help="Test case: 1 (duong cong), 2 (duong thang), 0 = ca 2")
    parser.add_argument("--no-display", action="store_true", help="Tat hien thi")
    parser.add_argument("--interval", "-i", type=int, default=10,
                       help="In debug moi N frame (1 = moi frame)")
    args = parser.parse_args()
    
    print(f"\n  === LANE CONTROL TEST DEBUG ===")
    print(f"  Thong so lane control:")
    print(f"  - STEERING_GAIN = {cfg.STEERING_GAIN}")
    print(f"  - MAX goc lai   = +/-{cfg.MAX_STEERING_ANGLE}°")
    print(f"  - Offset deadband = {cfg.OFFSET_DEADBAND}px")
    print(f"  - Lookahead: y={cfg.LOOKAHEAD_POINTS_Y}, w={cfg.LOOKAHEAD_POINTS_WEIGHTS}")
    print(f"  - Toc do: MAX={cfg.MAX_SPEED}%, NORM={cfg.NORMAL_SPEED}%, LOW={cfg.LOW_SPEED}%")
    print(f"  - Departure threshold = {cfg.DEPARTURE_THRESHOLD_PX}px")
    print(f"  - Hien thi: {'BAT' if not args.no_display else 'TAT'}")
    print(f"  - In debug moi: {args.interval} frame(s)\n")
    
    if args.testcase == 0:
        for tid in [1, 2]:
            chay_test(tid, show_display=not args.no_display,
                     debug_interval=args.interval)
    else:
        chay_test(args.testcase, show_display=not args.no_display,
                 debug_interval=args.interval)
    
    print("\n  === HOAN THANH ===")


if __name__ == "__main__":
    main()