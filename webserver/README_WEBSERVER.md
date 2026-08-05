# 🌐 Hướng Dẫn Chạy ADAS Web Dashboard

Dưới đây là các câu lệnh ngắn gọn để khởi chạy Web Dashboard.

## 🚀 1. Chạy trên PC (Chế độ mô phỏng / Simulation)
Sử dụng video test có sẵn, không yêu cầu phần cứng thật. Mở terminal và chạy các lệnh sau:

```bash
export PYTHONPATH="/home/donien/ADAS_STM32_Pi5/lane_and_trafficsign/ADAS_STM32_Pi5"
source /home/donien/ADAS_STM32_Pi5/venv/bin/activate
python /home/donien/ADAS_STM32_Pi5/lane_and_trafficsign/ADAS_STM32_Pi5/adas/app/main.py --simulate
```

## 🏎️ 2. Chạy trên Raspberry Pi 5 (Thực tế)
Tự động sử dụng camera thật (PiCamera) và kết nối UART với mạch STM32. 
*(Lưu ý: Cần chạy lệnh bằng `sudo` trỏ thẳng tới python trong môi trường ảo để có quyền truy cập camera, tránh lỗi Permission denied).*

Mở terminal và chạy:

```bash
export PYTHONPATH="/home/donien/ADAS_STM32_Pi5/lane_and_trafficsign/ADAS_STM32_Pi5"
sudo /home/donien/ADAS_STM32_Pi5/venv/bin/python /home/donien/ADAS_STM32_Pi5/lane_and_trafficsign/ADAS_STM32_Pi5/adas/app/main.py
```

## 🖥️ 3. Xem Giao Diện Web
Sau khi chạy thành công một trong hai phần trên, hãy mở trình duyệt web và truy cập:
- Trực tiếp trên máy đang chạy: `http://localhost:5000`
- Từ máy khác trong cùng mạng WiFi: `http://<IP_CỦA_MÁY_CHẠY>:5000`

### 🌍 Truy cập từ xa qua Internet (Ngrok)
Mở một terminal mới và chạy lệnh sau (lưu ý port 5000):
```bash
ngrok http --url=swimwear-vaguely-explain.ngrok-free.dev 5000
```
👉 Link truy cập web: **`https://swimwear-vaguely-explain.ngrok-free.dev`**
