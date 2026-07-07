"""
Test script to run lane detection on test_video.mp4.
Press 'q' to quit the live preview window.
Processes all frames even if lane detection fails on some frames.
"""

import cv2 as cv
import sys
import os
import traceback

try:
    from detector import LaneDetector
except ImportError:
    from .detector import LaneDetector


VIDEO_PATH = os.path.join(os.path.dirname(__file__), "test_video.mp4")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "output_test_video.mp4")


def main():
    # --- Open video ---
    cap = cv.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        print(f"[ERROR] Could not open video: {VIDEO_PATH}")
        sys.exit(1)

    # --- Video properties for output writer ---
    fps = cap.get(cv.CAP_PROP_FPS)
    width = int(cap.get(cv.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv.CAP_PROP_FRAME_COUNT))
    print(f"Video Info: {width}x{height}, {fps:.2f} FPS, {total_frames} frames")

    fourcc = cv.VideoWriter_fourcc(*"mp4v")
    out = cv.VideoWriter(OUTPUT_PATH, fourcc, fps, (width, height))

    # --- Lane detector ---
    detector = LaneDetector()

    frame_count = 0
    failed_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Process frame
        try:
            # return_debug=True returns (output, debug_view) tuple
            output, debug_view = detector.process_frame(frame, return_debug=True)
        except Exception as e:
            # If lane detection fails, write the original frame
            print(f"  [WARN] Frame {frame_count}: {e}")
            failed_count += 1
            output = frame
            debug_view = frame

        # Write to output video
        out.write(output)

        # Show live preview (2x2 composite: Input | Binary | Warped | Output)
        cv.imshow("Lane Detection Pipeline - test_video.mp4", debug_view)
        frame_count += 1

        # Progress every 100 frames
        if frame_count % 100 == 0:
            print(f"  Processed {frame_count}/{total_frames} frames "
                  f"(failures: {failed_count})")

        # Press 'q' to quit early
        if cv.waitKey(1) & 0xFF == ord("q"):
            print("  Quit requested by user.")
            break

    # --- Cleanup ---
    cap.release()
    out.release()
    cv.destroyAllWindows()

    print(f"\n[DONE] Processed {frame_count}/{total_frames} frames.")
    print(f"[DONE] Failed frames: {failed_count}/{frame_count}")
    print(f"[DONE] Output video saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()