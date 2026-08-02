#  Hướng Dẫn Sử Dụng ADAS Web Server

Tài liệu này giải thích cấu trúc kiến trúc web và cách khởi động giao diện điều khiển (Premium Dashboard) của hệ thống ADAS.

---

##  Cấu Trúc Thư Mục & Chức Năng

Hệ thống web được thiết kế theo mô hình phân lớp (tương tự MVC) để dễ dàng bảo trì và mở rộng. Dưới đây là chức năng của từng file trong thư mục `server/`:

- **`server.py` (Bộ điều khiển chính / Controller):** File cấu hình Flask. Nó định nghĩa các API và Router (ví dụ: `/api/status` để nhận/trả dữ liệu, `/video` để truyền hình ảnh).
- **`state.py` (Quản lý trạng thái xe / Model):** Hoạt động như một bộ nhớ đệm an toàn. Chứa biến `vehicle_state` và sử dụng Thread Lock để ngăn chặn xung đột dữ liệu khi hệ thống xe (bơm dữ liệu vào) và Web (đọc dữ liệu ra) hoạt động cùng lúc.
- **`stream.py` (Luồng hình ảnh):** Quản lý việc kết nối với Camera, nhúng thuật toán nhận diện làn đường, nén ảnh thành JPEG và liên tục phát (stream) video lên web.
- **`templates/index.html` (Khung giao diện / View):** File HTML thuần túy chứa bộ xương của Dashboard.
- **`static/css/style.css` (Giao diện / Styling):** File chứa toàn bộ code làm đẹp, màu sắc, hiệu ứng ánh sáng (neon/cyberpunk) và quy định font chữ.
- **`static/js/main.js` (Logic giao diện / Client-side):** Chạy trên trình duyệt của người dùng. Cứ mỗi 200ms nó sẽ gọi API `/api/status` một lần để lấy dữ liệu mới nhất và cập nhật lên màn hình.

---

##  Hướng Dẫn Khởi Động Hệ Thống

Để xem được dữ liệu chạy thật (như trên xe thực tế), bạn cần chạy 2 luồng song song: một luồng Web (để hiển thị) và một luồng Điều khiển (để bơm dữ liệu).

### Bước 1: Khởi động Màn Hình (Web Server)

Mở **Terminal 1** và chạy lệnh duy nhất sau để khởi động Web ở cổng `5000`:

```bash
cd /home/donien/ADAS_STM32_Pi5/lane_control_new/ADAS_STM32_Pi5/adas
sudo PYTHONPATH=$(pwd) /home/donien/ADAS_STM32_Pi5/venv/bin/python app/server/server.py
```
> Lúc này trang web đã có thể truy cập tại: `http://127.0.0.1:5000` (dữ liệu sẽ hiển thị `--`).

### Bước 2: Khởi động Luồng Nhận Diện (Bơm dữ liệu)

Mở **Terminal 2**, chạy script test để mô phỏng việc xe đang quét làn đường và liên tục bắn dữ liệu (POST) sang Web Server:

```bash
export PYTHONPATH="/home/donien/ADAS_STM32_Pi5/lane_control_new/ADAS_STM32_Pi5/adas" && source /home/donien/ADAS_STM32_Pi5/venv/bin/activate && python /home/donien/ADAS_STM32_Pi5/lane_control_new/ADAS_STM32_Pi5/adas/app/perception/lane/test_lane_control.py --simulate --no-display --loop
```
> *(--simulate: Chạy giả lập không cần mạch STM32; --no-display: Chạy ngầm; --loop: Chạy lặp lại vô tận).*

### Bước 3: Đưa Web ra Internet (Tùy chọn)

Mở **Terminal 3**, chạy Ngrok để lấy đường link gửi cho người khác xem (không cần chung mạng WiFi):

```bash
ngrok http 5000
```
*(Copy đường link có dạng `https://xxx.ngrok-free.app` để truy cập).*

---

##  Ý Nghĩa Các Thông Số Trên Web

- **Trạng thái hệ thống:** Báo hiệu tình trạng bám làn (Đang giữ làn, Chệch làn, hoặc Mất vạch).
- **Vận tốc & Vòng tua (RPM):** Thông số động cơ xe.
- **Góc lái (Steering):** Góc bẻ lái của Servo (%).
- **Lệnh Phanh:** Sẽ nhấp nháy đỏ `ĐANG PHANH` nếu gặp vật cản.
- **Siêu âm (Trái/Phải):** Khoảng cách vật cản (cm). Nếu hiện `MAX` tức là đường thoáng.

##  Lưu ý Quan Trọng
1. Tuyệt đối **không tắt các cửa sổ Terminal**, nếu tắt thì tiến trình tương ứng sẽ chết.
2. Web truyền hình ảnh trực tiếp (Video Streaming), chỉ nên cho **1-3 người xem cùng lúc** để tránh Raspberry Pi bị quá tải và giật lag mạng.
