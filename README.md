# STM32 to Raspberry Pi UART Communication Protocol

Tài liệu này quy định chi tiết cấu trúc gói tin (Packet format), thuật toán kiểm tra toàn vẹn (Checksum) và cấu hình lớp vật lý để kết nối Real-time giữa **STM32 (Cortex-M3)** và **Raspberry Pi**.

---

## ⚙️ 1. Cấu hình phần cứng (Hardware Configuration)

* **Baudrate:** `115200 bps`
* **Data bits:** `8`
* **Stop bits:** `1`
* **Parity:** `None`
* **Thứ tự Byte (Endianness):** `Little-Endian` (Byte thấp gửi trước).
* **Tần suất (Frequency):** * **STM32 TX (Đẩy lên Pi):** Chủ động gửi liên tục mỗi **20ms** (50Hz) sử dụng ngắt Interrupt/DMA.
  * **Pi RX (Gửi xuống STM32):** Khuyến nghị gửi lệnh điều khiển xuống với chu kỳ **20ms** tương ứng để đảm bảo tính đồng bộ hệ thống.

---

## 📥 2. Gói tin Lệnh từ Raspberry Pi gửi xuống STM32 (RX Packet - 8 Bytes)

Firmware STM32 sử dụng cơ chế **DMA Circular Buffer** quét liên tục theo dạng cửa sổ trượt (Sliding-window) để tìm cặp Header. Phía Raspberry Pi bắt buộc phải đóng gói dữ liệu chính xác 8 bytes theo cấu trúc không đệm (`#pragma pack(push, 1)`) dưới đây:

| Offset (Byte) | Tên trường (Field) | Kiểu dữ liệu | Kích thước | Mô tả / Giá trị |
| :---: | :--- | :---: | :---: | :--- |
| **0** | `header1` | `uint8_t` | 1 byte | Cố định **`0xAA`** (170) |
| **1** | `header2` | `uint8_t` | 1 byte | Cố định **`0x55`** (85) |
| **2** | `cmd_id` | `uint8_t` | 1 byte | ID của lệnh (Tùy chọn sử dụng làm marker) |
| **3 - 4** | `target_speed` | `int16_t` | 2 bytes | Vận tốc mục tiêu (Có dấu). Ví dụ: `-3599` đến `3599`. |
| **5** | `steering_error` | `int8_t` | 1 byte | Góc lái mục tiêu: Từ **`-100`** (Kịch Trái) đến **`100`** (Kịch Phải). |
| **6** | `brake_command` | `uint8_t` | 1 byte | **`1`**: Kích hoạt phanh khẩn cấp (E-Stop). <br>**`0`**: Chạy bình thường. |
| **7** | `checksum` | `uint8_t` | 1 byte | Byte kiểm tra lỗi (8-bit Sum). |

### 🧮 Quy tắc tính Checksum gói RX:
Tính tổng các byte dữ liệu từ **Offset 2** đến **Offset 6** (Phép cộng 8-bit, tự tràn số):
$$\text{checksum} = (\text{cmd\_id} + \text{target\_speed\_L} + \text{target\_speed\_H} + \text{steering\_error} + \text{brake\_command}) \pmod{256}$$

---

## 📤 3. Gói tin Telemetry từ STM32 báo cáo lên Raspberry Pi (TX Packet - 9 Bytes)

Mỗi 20ms, STM32 sẽ thu thập trạng thái cảm biến siêu âm và tốc độ thực tế từ Encoder để đóng gói gửi lên Pi.

| Offset (Byte) | Tên trường (Field) | Kiểu dữ liệu | Kích thước | Mô tả / Giá trị |
| :---: | :--- | :---: | :---: | :--- |
| **0** | `header1` | `uint8_t` | 1 byte | Cố định **`0xAA`** (170) |
| **1** | `header2` | `uint8_t` | 1 byte | Cố định **`0x55`** (85) |
| **2 - 3** | `distance_left` | `uint16_t` | 2 bytes | Khoảng cách cảm biến siêu âm Trái (cm). <br>Giá trị **`999`** = Lỗi phần cứng/Ngoài khoảng đo. |
| **4 - 5** | `distance_right`| `uint16_t` | 2 bytes | Khoảng cách cảm biến siêu âm Phải (cm). <br>Giá trị **`999`** = Lỗi phần cứng/Ngoài khoảng đo. |
| **6 - 7** | `actual_rpm` | `int16_t` | 2 bytes | Vận tốc thực tế hiện tại của xe (Tính qua Encoder, có dấu). |
| **8** | `checksum` | `uint8_t` | 1 byte | Byte kiểm tra lỗi (8-bit Sum). |

### 🧮 Quy tắc tính Checksum gói TX:
Tính tổng các byte dữ liệu từ **Offset 2** đến **Offset 7** (Phép cộng 8-bit, tự tràn số):
$$\text{checksum} = (\text{dist\_L\_bytes} + \text{dist\_R\_bytes} + \text{rpm\_bytes}) \pmod{256}$$

---

## 💡 4. Hướng dẫn lập trình triển khai cho phía Raspberry Pi (Tham khảo nhanh)

Để hỗ trợ team phần mềm phía Raspberry Pi kết nối nhanh gọn, dưới đây là ví dụ triển khai đóng gói và giải mã bằng ngôn ngữ **Python** (Sử dụng thư viện `pyserial` và `struct`):

### Khởi tạo kết nối
```python
import serial
import struct

# Cấu hình UART trên Raspberry Pi (Ví dụ dùng cổng /dev/ttyAMA0 hoặc /dev/ttyUSB0)
ser = serial.Serial(
    port='/dev/ttyAMA0',
    baudrate=115200,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=0.1
)
