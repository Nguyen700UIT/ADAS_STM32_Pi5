# 🏗️ Kiến Trúc Tổng Thể Dự Án ADAS STM32 Pi5

Dự án này là một hệ thống Tự hành toàn diện, kết hợp giữa **Thị giác Máy tính (AI trên Raspberry Pi)**, **Điều khiển nhúng (STM32)** và **Giao diện Giám sát (Web Dashboard)**.

Dưới đây là cấu trúc chi tiết từng thư mục và ý nghĩa của các file bên trong:

---

## 1. 🧠 `lane_and_trafficsign/` (Bộ Não Tự Hành)
Đây là nơi chứa toàn bộ mã nguồn xử lý AI và tính toán của xe. Chạy trực tiếp trên Raspberry Pi 5.

```text
lane_and_trafficsign/
└── ADAS_STM32_Pi5/
    └── adas/
        ├── app/                      # Lớp Ứng dụng & Production (Code chạy thật)
        │   ├── main.py               # File Entry-point: Gọi Camera, chạy AI, đẩy xuống UART và đẩy lên Web.
        │   │
        │   ├── perception/           # Lớp Nhận Diện (Đôi mắt)
        │   │   ├── lane_detector.py  # Xử lý ảnh OpenCV (Warp, Threshold, PolyFit) để tìm vạch kẻ đường.
        │   │   ├── sign_detector.py  # Xử lý AI YOLOv8 để tìm Biển báo giao thông.
        │   │   ├── aruco_detector.py # Xử lý OpenCV để quét đọc các ArUco Marker (định vị cục bộ).
        │   │   └── videos/           # Chứa các file .mp4 dùng để test mô phỏng.
        │   │
        │   ├── control/              # Lớp Điều Khiển (Chân tay)
        │   │   ├── lane_controller.py# Thuật toán Pure Pursuit tính góc bẻ vô lăng dựa trên tâm đường.
        │   │   └── sign_controller.py# Tính tốc độ phanh và góc bẻ lái tĩnh khi rẽ theo biển báo.
        │   │
        │   ├── decision/             # Lớp Ra Quyết Định (Máy trạng thái)
        │   │   ├── fusion.py         # Nhận biết khi nào nên bám làn, rẽ, phanh dựa trên Sensor Fusion.
        │   │   └── routing.py        # Thuật toán State-based Dijkstra tính toán lộ trình từ A->B.
        │   │
        │   ├── communication/        # Lớp Giao Tiếp (Phần cứng)
        │   │   ├── uart.py           # Đọc/Ghi dữ liệu Serial với mạch STM32.
        │   │   └── protocol.py       # Đóng gói/Giải nén Frame truyền 0xAA 0x55.
        │   │
        │   ├── camera/               # Lớp Giao Tiếp (Phần cứng)
        │   │   └── camera.py         # Tương tác với module PiCamera2.
        │   │
        │   └── config/               # Lớp Cấu Hình (Hằng số)
        │       ├── lane_config.py    # Tọa độ cắt ảnh (ROI), dải màu HSV.
        │       ├── lane_control_config.py # Thông số Pure Pursuit, tốc độ xe, hệ số PID.
        │       ├── sign_config.py    # Khai báo các class biển báo (stop, turn_left...).
        │       └── map_config.py     # Cấu hình bản đồ đồ thị số cho Dijkstra.
        │
        └── tests/                    # Sân tập: Chỉ dùng để test tính năng rời rạc
            ├── test_lane_control.py  # Test độc lập phần bám làn không có biển báo.
            ├── test_sign_control.py  # Test độc lập phần biển báo không có bám làn.
            ├── test_on_video.py      # Test lane cơ bản (Cũ).
            ├── test_offset_fix.py    # Test hiệu chỉnh độ lệch vô lăng.
            └── diagnose_offset.py    # Script vẽ biểu đồ, chẩn đoán lỗi lệch vô lăng.
```

---

## 2. 🌐 `webserver/` (Giao Diện Giám Sát HMI)
Hệ thống Web độc lập dùng để hiển thị dữ liệu (Telemetry) từ Raspberry Pi lên màn hình điện thoại hoặc máy tính.

```text
webserver/
├── server.py               # Khởi động Flask Server ở cổng 5000 và định tuyến các trang.
├── state.py                # Biến toàn cục (Global Variables) lưu trữ góc lái, tốc độ, trạng thái xe hiện tại.
├── stream.py               # Bơm luồng Video MJPEG từ Raspberry Pi lên giao diện Web.
├── README_WEBSERVER.md     # Tài liệu hướng dẫn câu lệnh khởi chạy Web (Đã được cập nhật).
│
├── templates/              # Giao diện HTML
│   └── index.html          # Trang Dashboard chính với cụm Vô lăng, Đồng hồ tốc độ.
│
└── static/                 # Tài nguyên tĩnh
    ├── css/style.css       # File thiết kế (Dark mode, giao diện mờ).
    ├── js/main.js          # File logic (Fetch JSON mỗi 100ms để xoay vô lăng, đổi số).
    └── images/             # Hình ảnh logo, vô lăng (steering-wheel.png)...
```

---

## 3. ⚙️ `line_detection/` (Firmware Điều Khiển STM32)
Nơi chứa code nhúng (C/C++) chạy trực tiếp trên vi điều khiển STM32. Trực tiếp điều khiển bánh xe và phần cứng cấp thấp.

```text
line_detection/
└── line_detection_stm32/
    ├── Core/Src/main.c     # Code chính của STM32: Nhận lệnh UART -> Chỉnh PWM Motor -> Đọc Siêu âm -> Gửi dội lại Pi.
    ├── README.md           # Tài liệu cực kỳ quan trọng ghi rõ sơ đồ đấu dây Pinout và cấu trúc Gói tin UART.
    └── (Các thư mục HAL)   # Thư viện giao tiếp phần cứng của STM32.
```

---

## 4. 🗺️ `mapADAS_4m/` (Công cụ Bản đồ & ArUco Marker)
Thư mục chứa các công cụ sinh bản đồ đồ thị số (Graph) và tạo file in ấn ArUco marker.

```text
mapADAS_4m/
├── map_tool.py             # Công cụ Tool GUI giúp click tọa độ trên ảnh để tạo bản đồ số.
├── map_config_generated.py # File output sinh ra từ tool chứa Graph và Bảng hành động (Action map).
├── generate_aruco_markers.py # Script Python dùng OpenCV để sinh ảnh ArUco Marker.
├── aruco_markers_ADAS.pdf  # File PDF đã tổng hợp để in ra dán lên sa bàn.
└── aruco_individual/       # Chứa các ảnh rời rạc của từng Marker ID (từ 1 -> 54).
```

---

## 5. 🗃️ Các File & Thư Mục Phụ Trợ (Nằm tại Root)

```text
/home/donien/ADAS_STM32_Pi5/
│
├── adas.service                         # File cấu hình Systemd: Giúp Raspberry Pi tự động chạy main.py khi cắm điện.
├── venv/                                # Môi trường ảo (Virtual Environment) chứa các thư viện Python.
├── yolov8n.pt                           # File Model AI mặc định của YOLO.
├── PROJECT_STRUCTURE.md                 # Chính là tài liệu này.
├── SYSTEM_DESIGN_Dijkstra_ArUco.md      # Tài liệu mô tả lý thuyết thuật toán Dijkstra + ArUco của dự án.
└── WORK_PLAN_Control_Train_Models.md    # Kế hoạch phát triển dự án chi tiết qua các giai đoạn.
```
