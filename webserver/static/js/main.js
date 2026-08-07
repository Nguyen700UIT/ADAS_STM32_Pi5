// ============================================================
// ADAS Dashboard — JavaScript Controller
// Cập nhật dữ liệu UART 2 chiều (TX: Pi→STM32, RX: STM32→Pi)
// ============================================================

// TX Elements (Pi → STM32)
const targetSpeedEl = document.getElementById("target_speed");
const steeringErrorEl = document.getElementById("steering_error");
const brakeCommandEl = document.getElementById("brake_command");
const cmdIdEl = document.getElementById("cmd_id");

// RX Elements (STM32 → Pi)
const distanceLeftEl = document.getElementById("distance_left");
const distanceRightEl = document.getElementById("distance_right");
const actualRpmEl = document.getElementById("actual_rpm");

// System Status Elements
const statusEl = document.getElementById("status");
const fusionStateEl = document.getElementById("fusion-state");
const detectedSignsEl = document.getElementById("detected-signs");
const updatedEl = document.getElementById("updated");
const connStatusEl = document.getElementById("conn-status");
const uartStatusEl = document.getElementById("uart-status");
const uartFreqEl = document.getElementById("uart-freq");

// Steering indicator element
const steeringMetric = document.getElementById("metric-steering");

// Track update frequency
let lastUpdateTime = Date.now();
let updateFreqs = [];

const FUSION_STATE_LABELS = {
    "idle": "Chờ khởi động",
    "lane_following": "Bám làn đường",
    "turning_left": "Đang rẽ trái",
    "turning_right": "Đang rẽ phải",
    "stopped": "Dừng xe",
};

function numberText(value, digits) {
    const number = Number(value);
    if (!Number.isFinite(number)) return "--";
    return number.toFixed(digits);
}

function formatDistance(value) {
    if (value === 999 || value === null || value === undefined) return "MAX";
    return numberText(value, 0);
}

async function refreshStatus() {
    try {
        const response = await fetch("/api/status", { cache: "no-store" });
        if (!response.ok) throw new Error("Mất kết nối");
        const data = await response.json();

        // ---- TX Data (Pi → STM32) ----
        targetSpeedEl.textContent = numberText(data.target_speed, 0);
        cmdIdEl.textContent = numberText(data.cmd_id, 0);

        // Steering Error with color indicator
        const steerVal = Number(data.steering_error);
        steeringErrorEl.textContent = numberText(data.steering_error, 0);
        if (steeringMetric) {
            if (Math.abs(steerVal) > 50) {
                steeringMetric.style.borderColor = "rgba(255, 234, 0, 0.5)";
            } else {
                steeringMetric.style.borderColor = "";
            }
        }

        // Brake Command
        if (data.brake_command) {
            brakeCommandEl.textContent = "ĐANG PHANH";
            brakeCommandEl.className = "status-pill danger";
        } else {
            brakeCommandEl.textContent = "NHẢ PHANH";
            brakeCommandEl.className = "status-pill";
            brakeCommandEl.style.background = "transparent";
            brakeCommandEl.style.color = "var(--ok)";
            brakeCommandEl.style.boxShadow = "none";
            brakeCommandEl.style.border = "1px solid var(--ok)";
        }

        // ---- RX Data (STM32 → Pi) ----
        actualRpmEl.textContent = numberText(data.actual_rpm, 0);
        distanceLeftEl.textContent = formatDistance(data.distance_left);
        distanceRightEl.textContent = formatDistance(data.distance_right);

        // Distance warning colors
        const distLeft = Number(data.distance_left);
        const distRight = Number(data.distance_right);
        const distLeftMetric = document.getElementById("metric-dist-left");
        const distRightMetric = document.getElementById("metric-dist-right");
        if (distLeftMetric) {
            distLeftMetric.style.borderColor = (distLeft < 30 && distLeft !== 999) ? "rgba(255, 23, 68, 0.5)" : "";
        }
        if (distRightMetric) {
            distRightMetric.style.borderColor = (distRight < 30 && distRight !== 999) ? "rgba(255, 23, 68, 0.5)" : "";
        }

        // ---- System Status ----
        // Fusion State
        const fsLabel = FUSION_STATE_LABELS[data.fusion_state] || data.fusion_state || "--";
        fusionStateEl.textContent = fsLabel;

        // Detected Signs
        if (data.detected_signs && data.detected_signs.length > 0) {
            detectedSignsEl.textContent = data.detected_signs.join(", ");
            detectedSignsEl.style.color = "var(--warning)";
        } else {
            detectedSignsEl.textContent = "Không có";
            detectedSignsEl.style.color = "var(--muted)";
        }

        // Lane Status Pill
        let statusText = data.status_text || "--";
        statusEl.textContent = statusText;
        if (data.status === 3 || data.status === 4) {
            statusEl.className = "status-pill warning";
        } else if (data.status === 0) {
            statusEl.className = "status-pill danger";
        } else {
            statusEl.className = "status-pill";
        }

        // UART Connection Status
        if (data.uart_connected) {
            uartStatusEl.innerHTML = '<div class="dot-uart connected"></div> UART: KẾT NỐI';
            uartStatusEl.style.color = "var(--ok)";
        } else {
            uartStatusEl.innerHTML = '<div class="dot-uart"></div> UART: SIMULATION';
            uartStatusEl.style.color = "var(--warning)";
        }

        // Web Connection Status
        connStatusEl.style.color = "var(--ok)";
        connStatusEl.innerHTML = '<div class="dot" style="background:var(--ok); box-shadow:0 0 10px var(--ok);"></div> ĐANG KẾT NỐI';

        // Update frequency tracking
        const now = Date.now();
        const dt = now - lastUpdateTime;
        lastUpdateTime = now;
        if (dt > 0 && dt < 5000) {
            updateFreqs.push(1000 / dt);
            if (updateFreqs.length > 10) updateFreqs.shift();
            const avgFreq = updateFreqs.reduce((a, b) => a + b, 0) / updateFreqs.length;
            uartFreqEl.textContent = numberText(avgFreq, 1);
        }

        updatedEl.textContent = "Cập nhật lúc: " + new Date().toLocaleTimeString("vi-VN") + "." + new Date().getMilliseconds().toString().padStart(3, '0');
    } catch (error) {
        connStatusEl.style.color = "var(--danger)";
        connStatusEl.innerHTML = '<div class="dot" style="background:var(--danger); box-shadow:0 0 10px var(--danger); animation:none;"></div> MẤT KẾT NỐI';
        updatedEl.textContent = "Đang thử kết nối lại...";
    }
}

refreshStatus();
setInterval(refreshStatus, 200);
