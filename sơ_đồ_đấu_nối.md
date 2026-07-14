# 3. Chi Tiết Đi Dây Toàn Hệ Thống (Thực Thi Vật Lý)

Tài liệu này là bản quy chuẩn thực thi đấu nối phần cứng. Bỏ qua mọi lý thuyết, yêu cầu thi công chính xác 100% theo các đầu mục dưới đây để đảm bảo tính ổn định của hệ thống.

## A. Nhánh 1 (Tải Nặng 12V - Động Cơ GA25)
*   **Cấp nguồn DRV8871:** Nối cổng **Đỏ** của Wago 1 vào chân **VM**. Nối cổng **Xanh** của Wago 1 vào chân **GND**.
*   **Kết nối động cơ:** Hàn trực tiếp dây lõi to từ cổng **OUT1** và **OUT2** của DRV8871 vào 2 tai kim loại (chổi than) của động cơ GA25.
*   **Xử lý jack Encoder:** Cắt sát gốc hoặc bọc kín băng keo cách điện cho Chân số 1 và Chân số 6 trên rắc cắm 6 chân của motor (bỏ trống hoàn toàn).
*   **Tín hiệu PWM:** Nối chân **IN1** của DRV8871 với **PA0** của STM32. Nối chân **IN2** với **PA1**.

## B. Nhánh 2 (Hạ Áp & Nguồn Logic 5V)
*   **Đầu vào XL4015:** Nối cổng **Đỏ** của Wago 1 vào **IN+**. Nối cổng **Xanh** của Wago 1 vào **IN-**.
*   **Cấu hình điện áp:** Vặn biến trở trên XL4015, dùng đồng hồ VOM đo ngõ ra đạt chính xác **5.0V** (tối đa 5.1V) trước khi cắm vào Wago 2.
*   **Đầu ra XL4015:** Nối **OUT+** vào cổng **Đỏ** của Wago 2. Nối **OUT-** vào cổng **Xanh** của Wago 2.

## C. Phân Phối Từ Wago 2 Ra 4 Linh Kiện
*   **STM32F103C8T6:** Cắm dây từ Wago 2 (Đỏ) vào chân **5V** (hoặc VIN). Cắm dây từ Wago 2 (Xanh) vào chân **GND**. Hàn song song cụm tụ lọc (100µF Hóa + 100nF Gốm) trực tiếp vào cặp chân 5V và GND này.
*   **Servo MG90S:** Cắm dây **Đỏ** (VCC) vào Wago 2 (Đỏ). Cắm dây **Nâu** (GND) vào Wago 2 (Xanh). Cắm dây **Cam** (PWM) vào **PB6**. Hàn tụ hóa 1000µF song song sát vào dây Đỏ và Nâu, cách thân Servo tối đa 3cm.
*   **HC-SR04 (Trái):** Nối **VCC** vào Wago 2 (Đỏ). Nối **GND** vào Wago 2 (Xanh). Nối **Trig** vào **PB8**. Nối **Echo** vào **PB7**.
*   **HC-SR04 (Phải):** Nối **VCC** vào Wago 2 (Đỏ). Nối **GND** vào Wago 2 (Xanh). Nối **Trig** vào **PB5**. Nối **Echo** vào **PB9**.

## D. Hệ Thống Tín Hiệu Khác (Mắt Đọc & Pi 5)
*   **Mắt đọc Encoder GA25:** Nối Chân 2 (GND) vào Wago 2 (Xanh). Nối Chân 5 (3.3V) vào chân **3.3V** của STM32. Nối Chân 3 (Phase A) vào **PA6**. Nối Chân 4 (Phase B) vào **PA7**.
*   **Raspberry Pi 5 (Cấp nguồn độc lập):** Nối chân **GND** (Pin 6 hoặc 9) chạy thẳng về **Wago 1 (Xanh)** để chốt Star Grounding. Nối chân **TX** (Pin 8) vào **PA10**. Nối chân **RX** (Pin 10) vào **PA9**.

---

# Quy Tắc An Toàn & Hướng Dẫn Vận Hành

## 1. An Toàn Đi Dây & Cỡ Dây (AWG)
*   **Tuyến tải nặng (Pin LiPo -> Wago 1 -> DRV8871 -> Motor):** Bắt buộc sử dụng dây lõi đồng nhiều sợi, cỡ dây từ **18 AWG đến 20 AWG**. Các mối hàn tại tai motor phải được bọc gen co nhiệt (ống gen) hoặc quấn băng keo cách điện kín hoàn toàn để chống chạm chập khi xe rung lắc.
*   **Tuyến tải nhẹ & Tín hiệu (XL4015, Wago 2, Sensor, Pi 5):** Sử dụng dây **24 AWG đến 26 AWG** (như cáp mạng, dây Dupont).
*   **Tuyệt đối không:** Cắm chung chân GND của Pi 5 vào Wago 2. Mọi nhiễu/dòng xả lớn bắt buộc phải thoát về nút trung tâm Wago 1.

## 2. An Toàn Pin LiPo 3S
*   **Giới hạn xả:** Cực kỳ lưu ý không để điện áp Pin LiPo tụt xuống dưới 11.1V (3.7V/cell). Bắt buộc phải gắn thêm mạch còi báo động tụt áp LiPo (Lipo Battery Checker Buzzer) vào cổng Balance của pin khi chạy xe.
*   **Quy tắc sạc:** Chỉ sử dụng bộ sạc cân bằng chuyên dụng (như Imax B6 hoặc B3) qua cổng Balance (rắc trắng 4 lỗ). Không tự ý chế nguồn 12V sạc trực tiếp.
*   **Phòng chống cháy nổ:** Ngừng sử dụng ngay lập tức nếu pin có dấu hiệu phồng rộp, biến dạng hoặc tỏa nhiệt bất thường lúc không hoạt động.

## 3. Cách Cấp Nguồn & Khởi Động Hệ Thống
*   **Trình tự khởi động (Power-up Sequence):** Bật nguồn cấp riêng cho Raspberry Pi 5 trước. Đợi Pi 5 boot xong hệ điều hành hoàn toàn. Sau đó mới cắm rắc Pin LiPo vào Wago 1 để cấp điện cho mảng phần cứng (STM32, Driver, Động cơ). Việc này giúp chân UART không bị nhiễu do trạng thái lơ lửng khi Pi chưa khởi động.
*   **Ngắt kết nối khi nạp code:** Khi cắm mạch nạp ST-LINK vào máy tính để flash/debug code cho STM32, **bắt buộc rút dây cấp nguồn 5V từ Wago 2 ra khỏi STM32**. Chỉ sử dụng 3 dây của ST-LINK: SWCLK, SWDIO, GND. Việc cắm song song cả nguồn Wago 2 và nguồn USB máy tính sẽ gây xung đột LDO, dẫn đến sập nguồn ST-LINK hoặc cháy cổng USB.
*   **Kiểm tra chập mạch (Continuity Check):** Trước khi cắm pin LiPo lần đầu tiên sau khi đi dây, dùng đồng hồ vạn năng vặn thang đo thông mạch (tiếng bíp). Đo thử giữa bên Đỏ và bên Xanh của Wago 1, Wago 2. Nếu đồng hồ kêu bíp bíp, hệ thống đang bị ngắn mạch, tuyệt đối không được cắm pin.
