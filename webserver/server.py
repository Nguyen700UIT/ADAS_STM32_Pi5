import threading
from flask import Flask, Response, jsonify, request, render_template
from .state import get_public_state, update_vehicle_state
from .stream import gen

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/api/status', methods=['GET', 'POST'])
def api_status():
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        update_vehicle_state(
            # TX fields
            cmd_id=data.get("cmd_id"),
            target_speed=data.get("target_speed", data.get("speed")),
            steering_error=data.get("steering_error", data.get("angle")),
            brake_command=data.get("brake_command"),
            # RX fields
            distance_left=data.get("distance_left"),
            distance_right=data.get("distance_right"),
            actual_rpm=data.get("actual_rpm"),
            # System status
            status=data.get("status", data.get("flags")),
            fusion_state=data.get("fusion_state"),
            detected_signs=data.get("detected_signs"),
            uart_connected=data.get("uart_connected"),
        )

    return jsonify(get_public_state())


@app.route('/video')
def video():
    return Response(gen(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


def start_dashboard_thread(host="0.0.0.0", port=5000):
    """Khởi chạy Flask webserver trong một luồng (thread) chạy ngầm."""
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    server_thread = threading.Thread(
        target=lambda: app.run(host=host, port=port, debug=False, use_reloader=False),
        daemon=True
    )
    server_thread.start()
    print(f"[*] Web Dashboard chạy ngầm tại http://{host}:{port}")
    return server_thread

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
