from flask import Flask, Response, jsonify, request, render_template
from state import get_public_state, update_vehicle_state
from stream import gen

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/api/status', methods=['GET', 'POST'])
def api_status():
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        update_vehicle_state(
            speed=data.get("speed", data.get("target_speed")),
            status=data.get("status", data.get("flags")),
            angle=data.get("angle", data.get("steering_error")),
            distance_left=data.get("distance_left"),
            distance_right=data.get("distance_right"),
            actual_rpm=data.get("actual_rpm"),
            brake_command=data.get("brake_command"),
        )

    return jsonify(get_public_state())


@app.route('/video')
def video():
    return Response(gen(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
