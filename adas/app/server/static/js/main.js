const speedEl = document.getElementById("speed");
const statusEl = document.getElementById("status");
const angleEl = document.getElementById("angle");
const distanceLeftEl = document.getElementById("distance_left");
const distanceRightEl = document.getElementById("distance_right");
const actualRpmEl = document.getElementById("actual_rpm");
const brakeCommandEl = document.getElementById("brake_command");
const updatedEl = document.getElementById("updated");
const connStatusEl = document.getElementById("conn-status");
const dotEl = document.querySelector(".dot");

function numberText(value, digits) {
    const number = Number(value);
    if (!Number.isFinite(number)) return "--";
    return number.toFixed(digits);
}

async function refreshStatus() {
    try {
        const response = await fetch("/api/status", { cache: "no-store" });
        if (!response.ok) throw new Error("Mất kết nối");
        const data = await response.json();

        speedEl.textContent = numberText(data.speed, 0);
        angleEl.textContent = numberText(data.angle, 1);
        distanceLeftEl.textContent = data.distance_left == 999 ? "MAX" : numberText(data.distance_left, 0);
        distanceRightEl.textContent = data.distance_right == 999 ? "MAX" : numberText(data.distance_right, 0);
        actualRpmEl.textContent = numberText(data.actual_rpm, 0);
        
        // Trạng thái giữ làn (Flags)
        let statusText = data.status_text || "--";
        statusEl.textContent = statusText;
        if (data.status === 3) {
            statusEl.className = "status-pill warning";
        } else if (data.status === 0) {
            statusEl.className = "status-pill danger";
        } else {
            statusEl.className = "status-pill";
        }
        
        // Trạng thái Phanh
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
        
        // Trạng thái kết nối
        connStatusEl.style.color = "var(--ok)";
        dotEl.style.background = "var(--ok)";
        dotEl.style.boxShadow = "0 0 10px var(--ok)";
        connStatusEl.innerHTML = '<div class="dot" style="background:var(--ok); box-shadow:0 0 10px var(--ok);"></div> ĐANG KẾT NỐI';
        
        updatedEl.textContent = "Cập nhật lúc: " + new Date().toLocaleTimeString("vi-VN") + "." + new Date().getMilliseconds().toString().padStart(3, '0');
    } catch (error) {
        connStatusEl.style.color = "var(--danger)";
        connStatusEl.innerHTML = '<div class="dot" style="background:var(--danger); box-shadow:0 0 10px var(--danger); animation:none;"></div> MẤT KẾT NỐI';
        updatedEl.textContent = "Đang thử kết nối lại...";
    }
}

refreshStatus();
setInterval(refreshStatus, 200); // Tăng tần suất cập nhật lên 200ms cho mượt mà
