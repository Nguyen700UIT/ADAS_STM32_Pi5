# 🚀 Báo Cáo Chi Tiết Triển Khai Logic Hệ Thống Dự Án AI_RACE (ADAS_STM32_Pi5)

Tài liệu này mô tả chi tiết toàn bộ các thành phần đã được lập trình, cấu trúc thư mục, và luồng logic hoạt động hoàn chỉnh của dự án xe tự hành AI_RACE.

---

## 🏗️ 1. Cấu Trúc Tổng Thể

Dự án được phân rã thành các phân hệ chính để đảm bảo tính module hóa:
1. **`lane_and_trafficsign/ADAS_STM32_Pi5/adas/app/`**: Não bộ hệ thống chạy trên Raspberry Pi 5. Đảm nhiệm AI, Thị giác máy tính (Computer Vision), Ra quyết định (Decision Making) và kết nối Web.
2. **`line_detection/line_detection_stm32/`**: Tủy sống hệ thống chạy trên STM32 (C/C++). Điều khiển trực tiếp các phần cứng vật lý (Motor DC, Servo, Siêu âm, Encoder) theo thời gian thực (Real-time).
3. **`mapADAS_4m/`**: Công cụ Mapping & Localization. Chứa script tạo ArUco Marker, vẽ bản đồ số để cung cấp cho thuật toán dẫn đường Dijkstra.
4. **`webserver/`**: Cổng giám sát trực quan HMI (Human-Machine Interface), sử dụng Flask để hiển thị Telemetry và luồng video từ xe qua nền web.

---

## 🧠 2. Phân Hệ High-level AI & Điều Khiển (Raspberry Pi 5)

File khởi chạy chính: `lane_and_trafficsign/ADAS_STM32_Pi5/adas/app/main.py`.

### 2.1. Lớp Nhận Diện (Perception)
Đóng vai trò là "Đôi mắt" của chiếc xe.
- **`lane_detector.py`:** Xử lý ảnh từ camera để tìm ra làn đường. Các bước logic:
  - Cắt vùng ảnh quan tâm (ROI).
  - Áp dụng các bộ lọc màu (HSV) hoặc Thresholding để bóc tách vạch kẻ đường.
  - Chuyển đổi phối cảnh (Perspective Warp) để có góc nhìn từ trên xuống (Bird-eye view).
  - Dùng thuật toán PolyFit hoặc Sliding Window để vẽ ra một đường cong trung tâm (`center_fitx`).
- **`sign_detector.py`:** Chạy mô hình YOLOv8 (`yolov8n.pt`) để quét các biển báo giao thông hoặc vật cản, trả về mảng nhãn nhận diện được (VD: `['stop', 'turn_left']`).
- **`aruco_detector.py`:** Nhận diện các tấm ArUco Marker (chuẩn `DICT_4X4_100`) dán tại các ngã tư/điểm đỗ để xác định xe đang ở Node ID nào trên bản đồ.

### 2.2. Lớp Điều Khiển (Control)
Đóng vai trò là "Tiểu não", dịch kết quả nhận diện thành góc lái và vận tốc mục tiêu.
- **`lane_controller.py`:** Đọc đường cong trung tâm (`center_fitx`) từ `lane_detector`, chạy thuật toán bám làn (như Pure Pursuit hoặc PID) để xuất ra góc bẻ vô lăng (`steering_angle`) nhằm giữ xe ở giữa làn.
- **`sign_controller.py`:** Quản lý các logic lái tĩnh/rẽ ép buộc khi có biển báo. Ví dụ: Nếu nhận diện `turn_left`, sẽ cấp lệnh bẻ lái cứng sang trái và điều chỉnh giảm vận tốc cho việc vào cua.

### 2.3. Lớp Ra Quyết Định (Decision & Navigation)
- **`routing.py`:** Thuật toán **Dijkstra kết hợp State-based**.
  - Đọc `GRAPH` và `ACTION_MAP` từ config. 
  - Tính toán quãng đường ngắn nhất từ Node hiện tại tới Node đích. 
  - Điểm đặc biệt của logic này là khả năng "nhớ" trạng thái ngã tư vừa đi qua để xuất ra hành động đúng đắn (Turn Left, Turn Right, Forward) tại ngã tư tiếp theo mà **không cho phép quay đầu xe (U-Turn)**.
- **`fusion.py` (FusionController):** Nhạc trưởng của hệ thống.
  - Thu thập kết quả từ mọi nơi: Làn đường, Biển báo YOLO, ArUco Marker ID.
  - Phân tích độ ưu tiên để ra quyết định trạng thái xe (`fusion_state`): Đang bám làn (`lane_following`), Dừng (`stopped`), hay Rẽ theo biển báo.
  - Quản lý quá trình hợp nhất lệnh điều khiển trước khi đẩy xuống UART.

### 2.4. Lớp Giao Tiếp (Communication)
- **`uart.py` & `protocol.py`:** Quản lý luồng giao tiếp Serial với STM32 (Baudrate 115200). Đóng gói dữ liệu ra (`[0xAA][0x55][cmd][speed][steering][brake][chksum]`) và giải mã dữ liệu vào từ STM32 (Distance left, right, rpm).

---

## ⚙️ 3. Phân Hệ Low-level Control (STM32 Firmware)

Được code trên ngôn ngữ C, xử lý theo thời gian thực, file chính `line_detection/line_detection_stm32/Core/Src/main.c`.

### 3.1. Tiếp Nhận & Phản Hồi Giao Thức
- **Nhận (RX - 8 Bytes):** Chạy trên chế độ ngắt **DMA Circular Buffer** giúp không sót lệnh. STM32 đọc 8 bytes, kiểm tra tính toàn vẹn (Checksum 8-bit). Nếu hợp lệ, nó sẽ chiết xuất lệnh vận tốc (`target_speed`), góc bẻ lái (`steering_error`) và lệnh phanh (`brake_command`).
- **Gửi (TX - 9 Bytes):** Cứ mỗi chu kỳ 20ms (50Hz), STM32 thu thập trạng thái cảm biến siêu âm (Trái/Phải) và tốc độ quay (RPM) qua Encoder động cơ, đóng gói với Header `0xAA 0x55` + Checksum rồi bắn ngược lên Pi.

### 3.2. Logic Điều Khiển Vật Lý Thực Tế
- **Cảm biến Siêu âm (HC-SR04):** Sử dụng các ngắt Timer (Input Capture) để đo độ rộng xung Echo. Logic có tích hợp Watchdog và tự động reset Timer để chống kẹt xung gây lag toàn hệ thống.
- **Máy Trạng Thái An Toàn (FSM):** Tại hàm `FSM_Update()`, nếu phát hiện vật cản từ siêu âm gần hơn ngưỡng nguy hiểm, xe sẽ tự động chèn cờ `brake_command = true` (cắt ngang lệnh của Pi) để ngăn ngừa tai nạn vật lý tuyệt đối.
- **Servo Cua Gắt (Slew-rate limit):** Cập nhật góc bánh xe. Việc điều khiển có áp dụng Slew-rate để mượt mà hóa việc bẻ lái, chống giật khục hư hỏng cơ khí. Đi kèm là thuật toán `Dynamics_Compensate_Speed()` tự động hãm vận tốc DC khi bẻ lái gắt nhằm tránh lật xe do lực ly tâm.
- **Kiểm Soát Vận Tốc Động Cơ (PID & DRV8871):**
  - Đọc phản hồi thực tế từ Encoder qua Timer Encoder Mode.
  - Đưa vào bộ PID (`speed_pid`) để tính toán sai số vòng quay. Khi gặp lệnh xả phanh, bộ PID sẽ được reset thông số Integral để chống vọt ga lố (Wind-up).
  - Đẩy PWM ra Driver động cơ DRV8871 với khả năng chạy H-Bridge và Active Brake.

---

## 🌐 4. Phân Hệ Giao Diện Web Giám Sát (Web Dashboard)

Chạy ngầm (Daemon Thread) trực tiếp bên trong `main.py` của Pi thông qua `webserver`.

- **`server.py`:** Flask app mở port 5000 (`http://<IP_Pi>:5000/`). Cung cấp các endpoint như `/api/status` cho việc lấy telemetry và `/video` cho luồng stream.
- **`state.py`:** Module lưu giữ cục bộ bản đồ trạng thái Telemetry với cơ chế `Lock` (Thread-safe) nhằm tránh lỗi race condition khi luồng AI và luồng Web truy cập đồng thời.
- **`stream.py`:** Dịch frame ảnh đã vẽ đè chữ (`annotated`) từ luồng xử lý AI thành chuỗi byte JPEG (MJPEG Multipart) và đẩy lên cho thẻ `<img>` phía Frontend hiển thị thời gian thực với độ trễ cực thấp.
- **Frontend (Static/Templates):** Trình duyệt web sử dụng kỹ thuật polling JSON (Ajax/Fetch API) để làm các Animation quay vô lăng ảo và đồng hồ tốc độ khớp với giá trị nhận được từ Pi & STM.

---

## 🗺️ 5. Phân Hệ Bản Đồ & Localization (mapADAS_4m)

- **`generate_aruco_markers.py`:** Script OpenCV sinh ra các hình ảnh ArUco Marker theo chuẩn `DICT_4X4_100` được định dạng trong PDF, hỗ trợ in ấn và dán tại các mép ngã tư trên sa bàn vật lý. Kích thước đề nghị 4x4cm hoặc 5x5cm.
- **`map_tool.py`:** Một công cụ Graphic GUI cho phép load ảnh sa bàn từ trên cao. Người dùng double-click tạo ngã tư, kéo thả để nối đường. Cứ 2 click sẽ tạo một cạnh trong Graph. Sau khi xử lý sẽ sinh tự động file `map_config_generated.py`.
- **`map_config_generated.py`:** Output của tool. Chứa Dictionary `GRAPH` (Danh sách Node và khoảng cách cạnh, phục vụ thuật toán Dijkstra tính đường ngắn nhất) và `ACTION_MAP` (Chứa Logic Rẽ dựa trên 3 Node liên tiếp `Prev -> Curr -> Next` => Cấp lệnh `TURN_LEFT`, `TURN_RIGHT` hoặc đi thẳng `FORWARD`).

---

## 🛠️ 6. Luồng Thực Thi Hoạt Động Cốt Lõi (End-to-End Logic Pipeline)

Luồng hoạt động khi chạy file `main.py` của toàn bộ hệ thống:

1. **Khởi động:** Bật Web Dashboard (chạy ngầm), Mở kết nối UART tới vi điều khiển STM32, Mở Camera.
2. **Theo dõi Làn đường:** Hệ thống thu thập khung hình từ camera, cắt, lọc ngưỡng và sử dụng thuật toán bám theo làn trên sa bàn (`lane_detector`).
3. **Quét Biển báo / Marker:** Song song với bám làn, `sign_detector` (YOLO) và `aruco_detector` liên tục hoạt động.
4. **Ra quyết định Cục bộ (Localization & Navigation):** Nếu Camera bắt được tấm bảng "ArUco ID = 5", lớp `fusion` ghi nhớ ID. Thuật toán `routing` dựa vào cấu hình `map_config`, biết được rằng để đến mục tiêu "Bãi Đỗ ID = 50", xe cần đi từ ngã tư 5 tới ngã tư kế tiếp là 6, và ra lệnh chuẩn bị `TURN_LEFT`.
5. **Gửi lệnh thực thi:** Khi đến ngã tư, hệ thống cấp phát lệnh RẼ TRÁI (vô lăng bẻ cực tả, vận tốc giảm nhẹ). `uart` đóng gói luồng byte gửi xuống STM32.
6. **Xử lý cấp thấp (Real-time):** STM32 liên tục nhận UART bằng DMA, phân rã gói tín hiệu ra thành mục tiêu `target_speed`, `steering_error`. Bỏ vào bộ lọc PID DC Motor và chỉnh PWM Servo, làm cho chiếc xe chuyển hướng một cách mượt mà nhờ thuật toán chống ly tâm và Slew-rate.
7. **Phản hồi và Hiển thị:** Cùng lúc, bộ đếm Encoder STM báo lại vòng tua thực tế và sóng siêu âm phản hồi có chướng ngại hay không về Pi. Toàn bộ thông tin được `state.py` ghi nhận lại và truyền ra Flask server để hiện lên giao diện Web, giúp người giám sát thấy góc bẻ lái, tốc độ và các HUD trạng thái hệ thống. 
8. **An toàn ngoại lệ:** Nếu trên đường, mô hình AI bắt gặp biển STOP, `fusion` sẽ đưa xe vào state `stopped`, phát cờ phanh cấp tốc xuống STM32 (Brake_Command=1). Tương tự cho các vật cản bất ngờ được siêu âm phát hiện. Web Server sẽ nhấp nháy đèn đỏ báo động.
