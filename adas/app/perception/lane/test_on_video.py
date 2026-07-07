"""
Test script to run lane detection on test_video.mp4.
Press 'q' to quit the live preview window.
"""

import cv2 as cv
import sys
import os
import traceback

try:
    from detector import LaneDetector
except ImportError:
    from .detector import LaneDetector


VIDEO_PATH = os.path.join(os.path.dirname(__file__), "VIDEO_GOC_TESTCASE_1.mp4")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "output_test_video.mp4")


def main():
    cap = cv.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        print(f"[ERROR] Could not open video: {VIDEO_PATH}")
        sys.exit(1)

    fps = cap.get(cv.CAP_PROP_FPS)
    width = int(cap.get(cv.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv.CAP_PROP_FRAME_COUNT))
    print(f"Video Info: {width}x{height}, {fps:.2f} FPS, {total_frames} frames")

    fourcc = cv.VideoWriter_fourcc(*"mp4v")
    out = cv.VideoWriter(OUTPUT_PATH, fourcc, fps, (width, height))

    detector = LaneDetector()
    frame_count = 0
    failed_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        try:
            annotated, _ = detector.process_frame(frame)
        except Exception as e:
            print(f"  [WARN] Frame {frame_count}: {e}")
            traceback.print_exc()
            failed_count += 1
            annotated = frame

        out.write(annotated)
        cv.imshow("Lane Detection - Output", annotated)
        frame_count += 1

        if frame_count % 100 == 0:
            print(f"  Processed {frame_count}/{total_frames} frames "
                  f"(failures: {failed_count})")

        if cv.waitKey(1) & 0xFF == ord("q"):
            print("  Quit requested by user.")
            break

    cap.release()
    out.release()
    cv.destroyAllWindows()

    print(f"\n[DONE] Processed {frame_count}/{total_frames} frames.")
    print(f"[DONE] Failed frames: {failed_count}/{frame_count}")
    print(f"[DONE] Output video saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()