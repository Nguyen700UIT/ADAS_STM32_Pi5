import cv2 as cv
from app.camera import Camera
from app.pipeline.pipeline import process
from state import update_vehicle_state

camera = Camera()

def _read_pipeline_result(result):
    if isinstance(result, tuple):
        frame = result[0]
        data = result[1] if len(result) > 1 and isinstance(result[1], dict) else {}
        update_vehicle_state(
            speed=data.get("speed", data.get("target_speed")),
            status=data.get("status", data.get("flags")),
            angle=data.get("angle", data.get("steering_error")),
            distance_left=data.get("distance_left"),
            distance_right=data.get("distance_right"),
            actual_rpm=data.get("actual_rpm"),
            brake_command=data.get("brake_command")
        )
        return frame

    return result

def gen():
    while True:
        frame = camera.get_frame()

        try:
            frame = _read_pipeline_result(process(frame))
        except Exception as e:
            # Fallback if pipeline fails (e.g. ValueError)
            print(f"[STREAM WARNING] Pipeline error: {e}")
            pass
            
        if frame is None:
            continue

        ret, buffer = cv.imencode('.jpg', frame)
        if not ret:
            continue

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
