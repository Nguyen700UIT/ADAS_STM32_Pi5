"""Quick diagnostic: does the offset bias come from warp geometry or from the video itself?"""
import cv2 as cv
import numpy as np
import sys
import os
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parents[4]
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

from adas.app.perception.lane.detector import LaneDetector
from adas.app.config import lane_config
from adas.app.config import lane_control_config as ctrl_cfg

W, H = 640, 480
detector = LaneDetector()
warp_matrix, inv_warp_matrix = detector._get_warp_matrices(W, H)

# --- Warp geometry analysis ---
src = np.float32(lane_config.WARP_SRC) * detector._point_scale(W, H)
dst = np.float32(lane_config.WARP_DST) * detector._point_scale(W, H)

print("=" * 70)
print("  WARP GEOMETRY ANALYSIS")
print("=" * 70)
print(f"\n  SRC points (camera view):")
for i, pt in enumerate(src):
    print(f"    [{i}] x={pt[0]:7.1f}  y={pt[1]:7.1f}")
src_bottom_cx = (src[0][0] + src[3][0]) / 2
src_top_cx = (src[1][0] + src[2][0]) / 2
print(f"  SRC bottom center x = {src_bottom_cx:.1f}  (image center = {W/2})")
print(f"  SRC top center x    = {src_top_cx:.1f}")

print(f"\n  DST points (warped view):")
for i, pt in enumerate(dst):
    print(f"    [{i}] x={pt[0]:7.1f}  y={pt[1]:7.1f}")
dst_cx = (dst[0][0] + dst[3][0]) / 2
print(f"  DST center x = {dst_cx:.1f}")

# --- Car center in warped space ---
car_pt = np.float32([[[W / 2, H - 1]]])
car_warped = cv.perspectiveTransform(car_pt, warp_matrix)
car_warped_x = car_warped[0, 0, 0]
car_warped_y = car_warped[0, 0, 1]
print(f"\n  Car center ({W/2}, {H-1}) -> warped ({car_warped_x:.1f}, {car_warped_y:.1f})")
print(f"  Offset of car-warped-x from DST center: {car_warped_x - dst_cx:+.1f} px")

# --- Where does the IMAGE center map at the SRC bottom y? ---
src_bottom_y = src[0][1]
car_at_src_y = np.float32([[[W / 2, src_bottom_y]]])
car_at_src_warped = cv.perspectiveTransform(car_at_src_y, warp_matrix)
print(f"\n  Car center at SRC bottom y ({W/2}, {src_bottom_y:.0f}) -> warped x = {car_at_src_warped[0,0,0]:.1f}")

# --- Inverse: where does DST center map BACK to camera view? ---
dst_center_pt = np.float32([[[dst_cx, H-1]]])
dst_center_back = cv.perspectiveTransform(dst_center_pt, inv_warp_matrix)
print(f"\n  DST center ({dst_cx:.0f}, {H-1}) -> camera ({dst_center_back[0,0,0]:.1f}, {dst_center_back[0,0,1]:.1f})")

# --- Process a few frames to see actual lane center positions ---
video_path = os.path.join(os.path.dirname(__file__), "VIDEO_GOC_TESTCASE_1.mp4")
if not os.path.isfile(video_path):
    print(f"\n  [SKIP] Video not found: {video_path}")
    sys.exit(0)

cap = cv.VideoCapture(video_path)
print(f"\n{'=' * 70}")
print("  LANE CENTER ANALYSIS (first 100 frames)")
print("=" * 70)

offsets = []
lane_centers = []
frame_idx = 0
while frame_idx < 100:
    ret, frame = cap.read()
    if not ret:
        break
    frame = cv.resize(frame, (W, H))
    frame_idx += 1

    try:
        _, data = detector.process_frame(frame)
    except:
        continue

    left_fit = data.get("left_fit")
    right_fit = data.get("right_fit")
    if left_fit is None or right_fit is None:
        continue

    ploty = np.linspace(0, H - 1, H)
    left_fitx = np.polyval(left_fit, ploty)
    right_fitx = np.polyval(right_fit, ploty)
    center_fitx = (left_fitx + right_fitx) / 2

    # Lane center at the bottom of the image (closest to car)
    lane_center_bottom = center_fitx[-1]
    lane_width_bottom = right_fitx[-1] - left_fitx[-1]

    # Blended offset (using lookahead points)
    blended = 0.0
    for ly, w in zip(ctrl_cfg.LOOKAHEAD_POINTS_Y, ctrl_cfg.LOOKAHEAD_POINTS_WEIGHTS):
        idx = np.argmin(np.abs(ploty - ly))
        blended += w * (center_fitx[idx] - car_warped_x)

    offsets.append(blended)
    lane_centers.append(lane_center_bottom)

    if frame_idx % 20 == 0:
        print(f"  Frame {frame_idx:3d}:  lane_center_bottom={lane_center_bottom:.1f}  "
              f"lane_width={lane_width_bottom:.1f}  "
              f"left={left_fitx[-1]:.1f}  right={right_fitx[-1]:.1f}  "
              f"offset={blended:+.1f}")

cap.release()

if offsets:
    print(f"\n  Mean lane center (bottom):  {np.mean(lane_centers):.1f}")
    print(f"  Car center (warped):       {car_warped_x:.1f}")
    print(f"  DST center:                {dst_cx:.1f}")
    print(f"  Mean offset:               {np.mean(offsets):+.1f}")
    print(f"  Offset = lane_center - car_warped_x")
    print(f"  => The lane center is {np.mean(lane_centers) - car_warped_x:+.1f} px to the right of car center (at bottom)")

print(f"\n{'=' * 70}")
print("  DIAGNOSIS")
print("=" * 70)
if offsets:
    mean_offset = np.mean(offsets)
    geo_bias = dst_cx - car_warped_x
    print(f"  Geometric bias (DST center - car warped x): {geo_bias:+.1f} px")
    print(f"  Measured offset mean:                       {mean_offset:+.1f} px")
    if abs(geo_bias) > 50 and abs(mean_offset - geo_bias) < 30:
        print(f"\n  => CONCLUSION: Offset ~= geometric bias.")
        print(f"     The lane center tracks the DST center, not the car center.")
        print(f"     The warp geometry is causing the bias.")
    else:
        print(f"\n  => CONCLUSION: Offset differs from geometric bias.")
        print(f"     The car is genuinely off-center in the video,")
        print(f"     OR the lane detection has a systematic error.")
