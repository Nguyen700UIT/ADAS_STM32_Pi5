import cv2 as cv
import time

global_frame = None

def set_global_frame(frame):
    global global_frame
    global_frame = frame

def gen():
    while True:
        if global_frame is None:
            time.sleep(0.05)
            continue

        ret, buffer = cv.imencode('.jpg', global_frame)
        if not ret:
            time.sleep(0.05)
            continue

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        
        # Limit framerate of the web stream to ~30fps
        time.sleep(0.03)
