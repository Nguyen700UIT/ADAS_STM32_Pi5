"""
Test Offset Normalization
=========================
Processes the test video with lane detection and compares
raw pixel offset vs normalized steering_error to verify the fix.

Outputs:
  1. Annotated video: output_offset_test.mp4
  2. Offset plot:     offset_plot.png

Usage:
    python test_offset_fix.py
    python test_offset_fix.py --video path/to/video.mp4
    python test_offset_fix.py --max-frames 200   # limit frames for speed
"""

import cv2 as cv
import sys
import os
import argparse
import numpy as np
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_APP_DIR = Path(__file__).resolve().parents[4]
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

from adas.app.perception.lane.detector import LaneDetector
from adas.app.config import lane_control_config as ctrl_cfg

# ---------------------------------------------------------------------------
_DEFAULT_VIDEO = os.path.join(os.path.dirname(__file__), "VIDEO_GOC_TESTCASE_1.mp4")
_OUTPUT_VIDEO = os.path.join(os.path.dirname(__file__), "output_offset_test.mp4")
_OUTPUT_PLOT = os.path.join(os.path.dirname(__file__), "offset_plot.png")


def parse_args():
    p = argparse.ArgumentParser(description="Test offset normalization fix")
    p.add_argument("--video", default=_DEFAULT_VIDEO, help="Input video")
    p.add_argument("--max-frames", type=int, default=0, help="Max frames to process (0=all)")
    p.add_argument("--display", action="store_true", help="Display the video while processing")
    return p.parse_args()


def calc_offset(center_fitx, ploty, img_center_warped):
    """Compute blended offset in pixels (warped space)."""
    if center_fitx is None or ploty is None:
        return 0.0
    blended = 0.0
    for ly, w in zip(ctrl_cfg.LOOKAHEAD_POINTS_Y, ctrl_cfg.LOOKAHEAD_POINTS_WEIGHTS):
        idx = np.argmin(np.abs(ploty - ly))
        blended += w * (center_fitx[idx] - img_center_warped)
    if abs(blended) < ctrl_cfg.OFFSET_DEADBAND:
        return 0.0
    return blended


def normalize_offset(raw_offset):
    """Normalize pixel offset to [-100, 100] steering error."""
    normalized = raw_offset / ctrl_cfg.MAX_OFFSET_PX * 100.0
    return int(max(-100, min(100, normalized)))


def draw_offset_hud(frame, raw_offset, steering_error, frame_idx, total_frames):
    """Draw comparison HUD on frame."""
    h, w = frame.shape[:2]
    overlay = frame.copy()

    # Semi-transparent top bar
    bar_h = 120
    cv.rectangle(overlay, (0, 0), (w, bar_h), (0, 0, 0), -1)
    cv.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

    # Frame counter
    cv.putText(frame, f"Frame: {frame_idx}/{total_frames}",
               (10, 25), cv.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)

    # Raw offset (BEFORE fix)
    old_steering = int(max(-100, min(100, raw_offset)))  # old behavior
    raw_color = (0, 0, 255) if abs(old_steering) >= 100 else (0, 255, 255)
    cv.putText(frame, f"BEFORE  raw_offset: {raw_offset:+7.1f}px  steering_error: {old_steering:+4d}",
               (10, 55), cv.FONT_HERSHEY_SIMPLEX, 0.55, raw_color, 2)

    # Normalized offset (AFTER fix)
    norm_color = (0, 255, 0) if abs(steering_error) < 80 else (0, 165, 255)
    cv.putText(frame, f"AFTER   raw_offset: {raw_offset:+7.1f}px  steering_error: {steering_error:+4d}",
               (10, 85), cv.FONT_HERSHEY_SIMPLEX, 0.55, norm_color, 2)

    # Config info
    cv.putText(frame, f"MAX_OFFSET_PX={ctrl_cfg.MAX_OFFSET_PX}",
               (w - 250, 25), cv.FONT_HERSHEY_SIMPLEX, 0.55, (180, 180, 180), 1)

    # ---- Offset bar visualization ----
    bar_y = bar_h + 15
    bar_center_x = w // 2
    bar_width = 400

    # Background bar
    cv.rectangle(frame,
                 (bar_center_x - bar_width // 2, bar_y),
                 (bar_center_x + bar_width // 2, bar_y + 24),
                 (40, 40, 40), -1)

    # Center line
    cv.line(frame, (bar_center_x, bar_y - 2), (bar_center_x, bar_y + 26),
            (255, 255, 255), 2)

    # "BEFORE" indicator (red triangle, top row)
    old_disp = np.clip(old_steering, -bar_width // 4, bar_width // 4)
    old_x = int(bar_center_x + old_disp * 2)
    pts_old = np.array([[old_x, bar_y + 2], [old_x - 6, bar_y + 10], [old_x + 6, bar_y + 10]], np.int32)
    cv.fillPoly(frame, [pts_old], (0, 0, 255))
    cv.putText(frame, "B", (old_x - 4, bar_y + 10), cv.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)

    # "AFTER" indicator (green triangle, bottom row)
    new_disp = np.clip(steering_error, -bar_width // 4, bar_width // 4)
    new_x = int(bar_center_x + new_disp * 2)
    pts_new = np.array([[new_x, bar_y + 22], [new_x - 6, bar_y + 14], [new_x + 6, bar_y + 14]], np.int32)
    cv.fillPoly(frame, [pts_new], (0, 255, 0))
    cv.putText(frame, "A", (new_x - 4, bar_y + 22), cv.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 0), 1)

    # Labels
    cv.putText(frame, "-100", (bar_center_x - bar_width // 2 - 10, bar_y + 40),
               cv.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
    cv.putText(frame, "0", (bar_center_x - 5, bar_y + 40),
               cv.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
    cv.putText(frame, "+100", (bar_center_x + bar_width // 2 - 20, bar_y + 40),
               cv.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)

    return frame


def save_offset_plot(raw_offsets, normalized_offsets, output_path):
    """Save a matplotlib plot comparing raw vs normalized offsets over time."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
        frames = range(len(raw_offsets))

        # Raw offset plot
        ax1.plot(frames, raw_offsets, color='red', alpha=0.7, linewidth=0.8, label='Raw pixel offset')
        ax1.axhline(y=100, color='orange', linestyle='--', alpha=0.5, label='Old clamp ±100')
        ax1.axhline(y=-100, color='orange', linestyle='--', alpha=0.5)
        ax1.axhline(y=ctrl_cfg.MAX_OFFSET_PX, color='blue', linestyle=':', alpha=0.5,
                     label=f'MAX_OFFSET_PX ±{ctrl_cfg.MAX_OFFSET_PX}')
        ax1.axhline(y=-ctrl_cfg.MAX_OFFSET_PX, color='blue', linestyle=':', alpha=0.5)
        ax1.set_ylabel('Raw Offset (pixels)')
        ax1.set_title('BEFORE Fix: Raw pixel offset (frequently exceeds ±100)')
        ax1.legend(loc='upper right')
        ax1.grid(True, alpha=0.3)

        # Normalized steering error plot
        ax2.plot(frames, normalized_offsets, color='green', alpha=0.7, linewidth=0.8,
                 label='Normalized steering_error')

        # Show what old behavior would have sent
        old_clamped = [int(max(-100, min(100, r))) for r in raw_offsets]
        ax2.plot(frames, old_clamped, color='red', alpha=0.4, linewidth=0.8,
                 label='Old steering_error (clamped)')

        ax2.axhline(y=100, color='gray', linestyle='--', alpha=0.3)
        ax2.axhline(y=-100, color='gray', linestyle='--', alpha=0.3)
        ax2.set_ylabel('Steering Error (-100 to 100)')
        ax2.set_xlabel('Frame')
        ax2.set_title('AFTER Fix: Normalized steering_error sent to STM32')
        ax2.legend(loc='upper right')
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(output_path, dpi=150)
        plt.close()
        print(f"[PLOT] Saved to: {output_path}")
    except ImportError:
        print("[WARN] matplotlib not available, skipping plot")


def main():
    args = parse_args()
    video_path = args.video
    if not os.path.isfile(video_path):
        print(f"[ERROR] Video not found: {video_path}")
        sys.exit(1)

    cap = cv.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[ERROR] Could not open: {video_path}")
        sys.exit(1)

    fps = cap.get(cv.CAP_PROP_FPS)
    original_width = int(cap.get(cv.CAP_PROP_FRAME_WIDTH))
    original_height = int(cap.get(cv.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv.CAP_PROP_FRAME_COUNT))
    if args.max_frames > 0:
        total_frames = min(total_frames, args.max_frames)

    # Force 640x480 to match hardware config
    width, height = 640, 480

    print(f"\n{'=' * 60}")
    print(f"  Offset Normalization Test")
    print(f"  Video:  {os.path.basename(video_path)} (Original: {original_width}x{original_height}, Resized: {width}x{height} @ {fps:.1f}fps)")
    print(f"  Frames: {total_frames}")
    print(f"  MAX_OFFSET_PX = {ctrl_cfg.MAX_OFFSET_PX}")
    print(f"{'=' * 60}\n")

    # Init detector & compute setpoint
    detector = LaneDetector()
    warp_matrix, _ = detector._get_warp_matrices(width, height)
    from adas.app.config import lane_config
    scale_x = width / lane_config.IMAGE_WIDTH
    dst_left = lane_config.WARP_DST[0][0] * scale_x
    dst_right = lane_config.WARP_DST[2][0] * scale_x
    img_center_warped = (dst_left + dst_right) / 2.0
    print(f"[INFO] Lane setpoint (center of WARP_DST) -> warped x = {img_center_warped:.1f}")

    # Video writer
    fourcc = cv.VideoWriter_fourcc(*"mp4v")
    out = cv.VideoWriter(_OUTPUT_VIDEO, fourcc, fps, (width, height))

    # Data collection
    raw_offsets = []
    normalized_offsets = []
    saturated_before = 0
    saturated_after = 0

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret or (args.max_frames > 0 and frame_idx >= args.max_frames):
            break
        frame_idx += 1

        # Resize to 640x480 to match hardware config
        frame = cv.resize(frame, (width, height))

        # Lane detection
        try:
            annotated, data = detector.process_frame(frame)
        except Exception as e:
            print(f"  [WARN] Frame {frame_idx}: {e}")
            annotated = frame.copy()
            data = {"left_fit": None, "right_fit": None, "valid": False}

        left_fit = data.get("left_fit")
        right_fit = data.get("right_fit")
        ploty = np.linspace(0, height - 1, height)

        center_fitx = None
        if left_fit is not None and right_fit is not None:
            left_fitx = np.polyval(left_fit, ploty)
            right_fitx = np.polyval(right_fit, ploty)
            center_fitx = (left_fitx + right_fitx) / 2

        # Compute offsets
        raw_offset = calc_offset(center_fitx, ploty, img_center_warped)
        steering_error = normalize_offset(raw_offset)

        # Track saturation
        old_clamped = int(max(-100, min(100, raw_offset)))
        if abs(old_clamped) >= 100 and abs(raw_offset) > 0:
            saturated_before += 1
        if abs(steering_error) >= 100 and abs(raw_offset) > 0:
            saturated_after += 1

        raw_offsets.append(raw_offset)
        normalized_offsets.append(steering_error)

        # Draw HUD
        annotated = draw_offset_hud(annotated, raw_offset, steering_error, frame_idx, total_frames)
        out.write(annotated)
        
        if args.display:
            cv.imshow("Offset Fix Test", annotated)
            if cv.waitKey(1) & 0xFF == ord('q'):
                break

        # Console log every N frames
        if frame_idx % max(1, int(fps)) == 0:
            old_se = int(max(-100, min(100, raw_offset)))
            print(f"  [{frame_idx:>5d}/{total_frames}]  raw={raw_offset:+7.1f}px  "
                  f"BEFORE={old_se:+4d}  AFTER={steering_error:+4d}")

    cap.release()
    out.release()

    # Stats
    valid_offsets = [r for r in raw_offsets if r != 0]
    print(f"\n{'=' * 60}")
    print(f"  RESULTS")
    print(f"{'=' * 60}")
    print(f"  Frames processed: {frame_idx}")
    print(f"  Frames with lane: {len(valid_offsets)}")
    if valid_offsets:
        print(f"  Raw offset range: [{min(valid_offsets):+.1f}, {max(valid_offsets):+.1f}] px")
        print(f"  Raw offset mean:  {np.mean(valid_offsets):+.1f} px")
        print(f"  Raw offset std:   {np.std(valid_offsets):.1f} px")
    print(f"")
    print(f"  BEFORE fix: {saturated_before}/{len(valid_offsets)} frames at max steering "
          f"({saturated_before/max(len(valid_offsets),1)*100:.1f}%)")
    print(f"  AFTER  fix: {saturated_after}/{len(valid_offsets)} frames at max steering "
          f"({saturated_after/max(len(valid_offsets),1)*100:.1f}%)")
    print(f"")
    print(f"  Output video: {_OUTPUT_VIDEO}")
    print(f"{'=' * 60}\n")

    # Save plot
    save_offset_plot(raw_offsets, normalized_offsets, _OUTPUT_PLOT)
    print("Done!")


if __name__ == "__main__":
    main()
