"""
ADAS Web Server - DEBUG MODE for Windows testing
- Sử dụng webcam hoặc ảnh giả nếu không có camera
- Giả lập dữ liệu speed/status/angle để test Dashboard
- Đơn vị tốc độ: cm/s
"""
from threading import Lock, Thread
from time import time, sleep

from flask import Flask, Response, jsonify, request
import cv2 as cv
import numpy as np

app = Flask(__name__)

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
    <title>ADAS Web Server - DEBUG</title>
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

        .debug-badge {
            display: inline-block;
            padding: 4px 10px;
            background: #fff3cd;
            color: #856404;
            border: 1px solid #ffeeba;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 700;
            margin-left: 12px;
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
            <h1 class="brand">WEB SERVER <span class="debug-badge">DEBUG</span></h1>
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


class DebugCamera:
    """Camera debug: dùng webcam nếu có, nếu không thì tạo ảnh giả"""
    def __init__(self):
        self.cap = cv.VideoCapture(0)
        if not self.cap.isOpened():
            print("[DEBUG] Không tìm thấy webcam, dùng ảnh giả")
            self.use_dummy = True
        else:
            self.use_dummy = False
            print("[DEBUG] Đã kết nối webcam")

    def get_frame(self):
        if self.use_dummy:
            # Tạo ảnh giả màu xám với dòng chữ
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            frame[:] = (30, 30, 30)
            cv.putText(frame, "DEBUG MODE - No Camera", (120, 240),
                       cv.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            return frame
        ret, frame = self.cap.read()
        if not ret:
            return self.get_frame()
        return frame


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


def simulate_data():
    """Thread giả lập dữ liệu speed/status/angle thay đổi liên tục"""
    t = 0
    while True:
        # Tốc độ: 0 - 50 cm/s (thay đổi hình sin)
        speed = round(20.0 + 25.0 * abs(np.sin(t * 0.3)), 2)
        # Góc lái: -30 đến +30 độ
        angle = round(25.0 * np.sin(t * 0.5), 1)
        
        # Trạng thái thay đổi tuần hoàn
        status_cycle = [0, 1, 1, 2, 1, 3, 1, 4, 1]
        status = status_cycle[int(t) % len(status_cycle)]
        
        update_vehicle_state(speed=speed, status=status, angle=angle)
        
        t += 1
        sleep(1.0)


camera = DebugCamera()


def gen():
    while True:
        frame = camera.get_frame()
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
    print("=" * 50)
    print("ADAS SERVER - DEBUG MODE")
    print("=" * 50)
    print("Mở trình duyệt: http://localhost:5000")
    print("Nhấn Ctrl+C để dừng")
    print("=" * 50)
    
    # Chạy thread giả lập dữ liệu
    sim_thread = Thread(target=simulate_data, daemon=True)
    sim_thread.start()
    
    app.run(host="0.0.0.0", port=5000, debug=True)