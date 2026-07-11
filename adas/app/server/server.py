from threading import Lock
from time import time

from flask import Flask, Response, jsonify, request
import cv2 as cv
from app.camera import Camera
from app.pipeline import process

app = Flask(__name__)
camera = Camera()

STATUS_LABELS = {
    0: "Đứng yên",
    1: "Đi thẳng",
    2: "Quẹo trái",
    3: "Quẹo phải",
    4: "Đi lùi",
}

state_lock = Lock()
vehicle_state = {
    "speed": 0.0,
    "status": 0,
    "angle": 0.0,
    "updated_at": time(),
}

DASHBOARD_HTML = """
<!doctype html>
<html lang="vi">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>ADAS Web Server</title>
    <style>
        :root {
            --bg: #f5f7fb;
            --panel: #ffffff;
            --ink: #172033;
            --muted: #697386;
            --line: #d9e1ee;
            --accent: #1976d2;
            --accent-soft: #e7f1ff;
            --ok: #0f8f68;
        }

        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            min-height: 100vh;
            background:
                radial-gradient(circle at 1px 1px, rgba(23, 32, 51, 0.08) 1px, transparent 0),
                var(--bg);
            background-size: 18px 18px;
            color: var(--ink);
            font-family: Arial, Helvetica, sans-serif;
        }

        .dashboard {
            width: min(1120px, calc(100% - 32px));
            min-height: calc(100vh - 40px);
            margin: 20px auto;
            padding: 28px;
            display: grid;
            grid-template-columns: minmax(0, 1.45fr) minmax(280px, 0.85fr);
            gap: 28px;
            align-items: center;
            background: rgba(255, 255, 255, 0.86);
            border: 1px solid var(--line);
            border-radius: 8px;
            box-shadow: 0 18px 48px rgba(26, 40, 68, 0.12);
        }

        .brand {
            margin: 0 0 18px;
            font-size: 22px;
            font-weight: 700;
            letter-spacing: 0;
        }

        .stream-wrap {
            width: 100%;
        }

        .stream-frame {
            width: 100%;
            aspect-ratio: 16 / 9;
            overflow: hidden;
            background: #0c111a;
            border: 2px solid #1b2638;
            border-radius: 4px;
        }

        .stream-frame img {
            display: block;
            width: 100%;
            height: 100%;
            object-fit: contain;
        }

        .stream-caption {
            margin: 16px 0 0;
            text-align: center;
            font-size: 18px;
            font-weight: 700;
        }

        .telemetry {
            display: grid;
            gap: 18px;
        }

        .metric {
            padding: 18px;
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 8px;
        }

        .metric-label {
            margin: 0 0 8px;
            color: var(--muted);
            font-size: 15px;
            font-weight: 700;
        }

        .metric-value {
            margin: 0;
            font-size: 28px;
            font-weight: 800;
            line-height: 1.2;
        }

        .metric-value small {
            color: var(--muted);
            font-size: 16px;
            font-weight: 700;
        }

        .status-pill {
            display: inline-flex;
            align-items: center;
            min-height: 38px;
            padding: 6px 12px;
            color: var(--ok);
            background: #e9f8f3;
            border: 1px solid #bde7d8;
            border-radius: 999px;
            font-size: 18px;
            font-weight: 800;
        }

        .updated {
            color: var(--muted);
            font-size: 13px;
        }

        @media (max-width: 820px) {
            .dashboard {
                grid-template-columns: 1fr;
                align-items: start;
                padding: 18px;
            }

            .brand {
                font-size: 20px;
            }

            .metric-value {
                font-size: 24px;
            }
        }
    </style>
</head>
<body>
    <main class="dashboard">
        <section class="stream-wrap" aria-label="Màn hình stream">
            <h1 class="brand">WEB SERVER</h1>
            <div class="stream-frame">
                <img src="/video" alt="Camera stream ADAS">
            </div>
            <p class="stream-caption">MÀN HÌNH STREAM</p>
        </section>

        <aside class="telemetry" aria-label="Thông tin xe">
            <div class="metric">
                <p class="metric-label">Tốc độ xe</p>
                <p class="metric-value"><span id="speed">--</span> <small>cm/s</small></p>
            </div>

            <div class="metric">
                <p class="metric-label">Trạng thái xe</p>
                <p class="metric-value"><span id="status" class="status-pill">--</span></p>
            </div>

            <div class="metric">
                <p class="metric-label">Góc lái</p>
                <p class="metric-value"><span id="angle">--</span> <small>độ</small></p>
            </div>

            <div class="updated" id="updated">Đang chờ dữ liệu...</div>
        </aside>
    </main>

    <script>
        const speedEl = document.getElementById("speed");
        const statusEl = document.getElementById("status");
        const angleEl = document.getElementById("angle");
        const updatedEl = document.getElementById("updated");

        function numberText(value, digits) {
            const number = Number(value);
            if (!Number.isFinite(number)) {
                return "--";
            }
            return number.toFixed(digits);
        }

        async function refreshStatus() {
            try {
                const response = await fetch("/api/status", { cache: "no-store" });
                const data = await response.json();

                speedEl.textContent = numberText(data.speed, 2);
                statusEl.textContent = data.status_text || "--";
                angleEl.textContent = numberText(data.angle, 1);
                updatedEl.textContent = "Cập nhật: " + new Date().toLocaleTimeString("vi-VN");
            } catch (error) {
                updatedEl.textContent = "Mất kết nối dữ liệu";
            }
        }

        refreshStatus();
        setInterval(refreshStatus, 500);
    </script>
</body>
</html>
"""


def _public_state():
    with state_lock:
        state = dict(vehicle_state)

    status = int(state.get("status", 0))
    state["status_text"] = STATUS_LABELS.get(status, "Không xác định")
    return state


def update_vehicle_state(speed=None, status=None, angle=None):
    with state_lock:
        if speed is not None:
            vehicle_state["speed"] = float(speed)
        if status is not None:
            vehicle_state["status"] = int(status)
        if angle is not None:
            vehicle_state["angle"] = float(angle)
        vehicle_state["updated_at"] = time()


def _read_pipeline_result(result):
    if isinstance(result, tuple):
        frame = result[0]
        data = result[1] if len(result) > 1 and isinstance(result[1], dict) else {}
        update_vehicle_state(
            speed=data.get("speed"),
            status=data.get("status"),
            angle=data.get("angle", data.get("steering_angle")),
        )
        return frame

    return result


def gen():
    while True:
        frame = camera.get_frame()

        frame = _read_pipeline_result(process(frame))
        if frame is None:
            continue

        ret, buffer = cv.imencode('.jpg', frame)
        if not ret:
            continue

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')


@app.route('/')
def home():
    return DASHBOARD_HTML


@app.route('/api/status', methods=['GET', 'POST'])
def api_status():
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        update_vehicle_state(
            speed=data.get("speed"),
            status=data.get("status"),
            angle=data.get("angle"),
        )

    return jsonify(_public_state())


@app.route('/video')
def video():
    return Response(gen(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
