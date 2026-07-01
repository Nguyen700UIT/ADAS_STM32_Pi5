import importlib
import types
import pathlib
import sys
import unittest

try:
    import cv2 as cv
    import numpy as np
except ImportError:
    cv = None
    np = None


LANE_DIR = pathlib.Path(__file__).resolve().parent
if str(LANE_DIR) not in sys.path:
    sys.path.insert(0, str(LANE_DIR))


def install_cv2_stub():
    if cv is not None or "cv2" in sys.modules:
        return

    cv2 = types.SimpleNamespace()
    cv2.getPerspectiveTransform = lambda src, dst: np.eye(3, dtype=np.float32)
    sys.modules["cv2"] = cv2


class LaneDetectorTests(unittest.TestCase):
    def setUp(self):
        if np is None:
            self.skipTest("numpy is required for lane detector tests")

    def _load_detector_module(self):
        install_cv2_stub()
        sys.modules.pop("detector", None)
        return importlib.import_module("detector")

    def test_import_does_not_start_camera_hardware(self):
        detector = self._load_detector_module()
        self.assertTrue(hasattr(detector, "LaneDetector"))

    def test_sliding_windows_returns_debug_windows_and_x_of_y_fits(self):
        detector = self._load_detector_module()
        lane_detector = detector.LaneDetector()
        lane_detector.n_windows = 5
        lane_detector.margin = 12
        lane_detector.min_pixels = 2

        binary = np.zeros((100, 200), dtype=np.uint8)
        binary[:, 48:53] = 255
        binary[:, 148:153] = 255

        left_fit, right_fit, debug = lane_detector.sliding_windows(
            binary,
            left_base=50,
            right_base=150,
            return_debug=True,
        )

        self.assertEqual(len(debug["windows"]), 5)
        self.assertGreater(debug["left_inds"].size, 0)
        self.assertGreater(debug["right_inds"].size, 0)
        self.assertAlmostEqual(np.polyval(left_fit, 90), 50, delta=2)
        self.assertAlmostEqual(np.polyval(right_fit, 90), 150, delta=2)

    def test_smooth_fit_uses_current_sample_alpha(self):
        detector = self._load_detector_module()
        lane_detector = detector.LaneDetector()
        lane_detector.smoothing_alpha = 0.3

        previous = np.array([10.0, 10.0, 10.0])
        current = np.array([20.0, 20.0, 20.0])

        smoothed = lane_detector.smooth_fit(current, previous)

        np.testing.assert_allclose(smoothed, np.array([13.0, 13.0, 13.0]))

    def test_thresholding_detects_lane_markings_in_sample_video(self):
        if cv is None:
            self.skipTest("opencv is required for sample video threshold test")

        detector = self._load_detector_module()
        lane_detector = detector.LaneDetector()
        cap = cv.VideoCapture(str(LANE_DIR / "VIDEO_GOC_TESTCASE_1.mp4"))
        ok, frame = cap.read()
        cap.release()

        self.assertTrue(ok)
        warped = lane_detector.warp_perspective(lane_detector.preprocess(frame))
        binary = lane_detector.thresholding(warped)

        self.assertGreater(np.count_nonzero(binary), binary.size * 0.001)

    def test_process_frame_finds_valid_lane_in_sample_video(self):
        if cv is None:
            self.skipTest("opencv is required for sample video pipeline test")

        detector = self._load_detector_module()
        lane_detector = detector.LaneDetector()
        cap = cv.VideoCapture(str(LANE_DIR / "VIDEO_GOC_TESTCASE_1.mp4"))
        ok, frame = cap.read()
        cap.release()

        self.assertTrue(ok)
        _, data = lane_detector.process_frame(frame)

        self.assertTrue(data["valid"])


if __name__ == "__main__":
    unittest.main()
