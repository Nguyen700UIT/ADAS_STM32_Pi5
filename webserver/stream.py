import cv2 as cv
import time
import threading

_frame_lock = threading.Lock()
_global_frame = None

def set_global_frame(frame):
    global _global_frame
    with _frame_lock:
        _global_frame = frame.copy() if frame is not None else None

def gen():
    while True:
        with _frame_lock:
            frame = _global_frame.copy() if _global_frame is not None else None

        if frame is None:
            time.sleep(0.05)
            continue

        ret, buffer = cv.imencode('.jpg', frame)
        if not ret:
            time.sleep(0.05)
            continue

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        
        # Limit framerate of the web stream to ~30fps
        time.sleep(0.03)
