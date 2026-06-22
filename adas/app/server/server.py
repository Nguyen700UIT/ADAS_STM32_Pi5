from flask import Flask, Response
import cv2 as cv
from app.camera import Camera
from app.pipeline import process

app = Flask(__name__)
camera = Camera()

def gen():
    while True:
        frame = camera.get_frame()

        frame = process(frame)

        ret, buffer = cv.imencode('.jpg', frame)
        if not ret:
            continue

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')


@app.route('/')
def home():
    return "ADAS running"

@app.route('/video')
def video():
    return Response(gen(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)