from picamera2 import Picamera2

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
        return self.picam2.capture_array()