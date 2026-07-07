import argparse
from pathlib import Path

import cv2 as cv

from detector import LaneDetector


DEFAULT_VIDEO = Path(__file__).with_name("VIDEO_GOC_TESTCASE_1.mp4")

def parse_args():
    parser = argparse.ArgumentParser(description="Live lane detector visualization.")
    parser.add_argument(
        "--video",
        type=Path,
        default=DEFAULT_VIDEO,
        help="Path to input video.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    cap = cv.VideoCapture(str(args.video))
    if not cap.isOpened():
        raise SystemExit(f"Could not open video: {args.video}")

    detector = LaneDetector()
    fps = cap.get(cv.CAP_PROP_FPS)
    delay_ms = max(1, int(1000 / fps)) if fps and fps > 0 else 30

    cv.namedWindow("Lane Overlay", cv.WINDOW_NORMAL)
    cv.namedWindow("Warp Source", cv.WINDOW_NORMAL)
    cv.namedWindow("Warped", cv.WINDOW_NORMAL)
    cv.namedWindow("Binary", cv.WINDOW_NORMAL)
    cv.namedWindow("Sliding Windows", cv.WINDOW_NORMAL)

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        overlay, data = detector.process_frame(frame)

        cv.imshow("Lane Overlay", overlay)
        cv.imshow("Warp Source", data["warp_source"])
        cv.imshow("Warped", data["warped"])
        cv.imshow("Binary", data["binary"])
        cv.imshow("Sliding Windows", data["sliding_windows"])

        key = cv.waitKey(delay_ms) & 0xFF
        if key in (ord("q"), 27):
            break

    cap.release()
    cv.destroyAllWindows()


if __name__ == "__main__":
    main()
