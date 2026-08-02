try:
    from .camera import Camera
except ModuleNotFoundError:
    print("[WARNING] picamera2 not found. Camera is disabled (Running in PC test mode).")
    import numpy as np

    class Camera:
        def __init__(self):
            # Create a simple 480x640 black frame with text
            self.blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            import cv2
            cv2.putText(self.blank_frame, 'CAMERA DISABLED (NO PI)', (100, 240), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
        def get_frame(self):
            return self.blank_frame.copy()
