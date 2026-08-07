from picamera2 import Picamera2
import cv2 as cv

class Camera:
    def __init__(self):
        self.picam2 = Picamera2()
        self.picam2.configure(
            self.picam2.create_preview_configuration(
                main={"format": "RGB888", "size": (640, 480)}
            )
        )
        self.picam2.start()

    def get_frame(self):
        frame = self.picam2.capture_array()
        if frame is None:
            return None
        # PiCamera2 RGB888 trả về RGB, nhưng OpenCV xử lý BGR
        return cv.cvtColor(frame, cv.COLOR_RGB2BGR)