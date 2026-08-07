# Kế Hoạch Triển Khai AI & Dữ Liệu (ADAS Project)

Dựa trên phân tích yêu cầu từ các tin nhắn thảo luận của team, dưới đây là tài liệu mô tả chi tiết các công việc và các giai đoạn cần thực hiện để hoàn thiện hệ thống nhận diện làn đường (Lane Detection), phát hiện vật thể (Object Detection - Biển báo, Vật cản) và hệ thống dẫn đường tự động (Dijkstra + ArUco).

---

## Giai Đoạn 1: Tinh chỉnh thuật toán nhận diện làn đường (Lane Detector Tuning)
**Mục tiêu:** Đảm bảo xe có thể bám làn ổn định trước khi xử lý các vật thể phức tạp.
**Phân tích tin nhắn:** *"Giờ là chụp mấy frame hay quay 1 cái video bth cho tụi nó tune cái lane detector trước"*

* **Công việc cụ thể:**
  1. **Quay Video Thực Tế:** Đưa xe ra sa bàn (chỉ có đường, chưa cần đặt biển báo/vật cản). Chạy script để quay lại một video bình thường (video liên tục) ở góc nhìn của camera trên xe.
  2. **Chạy Test Offline:** Truyền video này vào các script test offline (như `test_on_video.py` hoặc `test_lane_control.py`) trên máy tính.
  3. **Tuning Thông Số (Tuning):** Căn chỉnh các dải màu (HSV), vùng quan tâm (ROI - Region of Interest), thông số Canny/Hough Transform và đặc biệt là hệ số PID cho góc lái.
* **File/Folder liên quan (cần cập nhật sau khi tune):**
  * `lane_and_trafficsign/ADAS_STM32_Pi5/adas/app/config/lane_config.py`
  * `lane_and_trafficsign/ADAS_STM32_Pi5/adas/app/config/lane_control_config.py`

---

## Giai Đoạn 2: Triển khai Hệ thống Dẫn đường ArUco + Dijkstra (Navigation System)
**Mục tiêu:** In, dán ArUco Marker lên sa bàn và kiểm tra xe tự dẫn đường đến đích.
**Trạng thái phần mềm:** ✅ Đã hoàn thành toàn bộ code (`map_config.py`, `aruco_detector.py`, `routing.py`, `fusion.py`).phân tích toàn bộ dự án c

* **Công việc cụ thể:**
  1. **In ArUco Marker:** Chạy script `mapADAS_4m/generate_aruco_markers.py` để sinh ra file PDF chứa 23 tấm Marker chuẩn `DICT_4X4_100`. Các ID cần in: `1-18` (ngã tư) và `50-54` (bãi đỗ). Kích thước mỗi tấm: **4x4 cm đến 5x5 cm**.
  2. **Cắt và Dán Marker lên Sa bàn:**
     - Chỉ dán **1 tấm duy nhất** cho mỗi ngã tư / bãi đỗ.
     - **Vị trí dán:** Lệch về phía xe hay đi tới (cách tâm ngã tư 15-20cm), sao cho camera nhìn thấy Marker khi xe còn cách ngã tư một khoảng an toàn.
     - Không dán ở ngay tâm ngã tư (vì đầu xe sẽ che khuất).
  3. **Calibrate Camera & Marker:**
     - Chạy xe thử qua vài ngã tư, quan sát trên Web Dashboard xem camera có đọc được ID Marker không.
     - Nếu camera không nhận diện được từ xa → tăng kích thước marker lên 5x5cm hoặc chỉnh thông số `adaptiveThreshWinSizeMin/Max` trong `aruco_detector.py`.
  4. **Test Dẫn đường End-to-End:**
     - Trong code `main.py`, gọi `fusion_ctrl.set_destination(54)` (ví dụ: đi đến bãi đỗ 54).
     - Quan sát xe tự động bám làn, đọc ArUco, tính Dijkstra, rẽ đúng hướng và dừng lại khi đến đích.
     - Kiểm tra trên Web Dashboard: HUD Navigation hiển thị Marker ID, Action, Path.
* **File/Folder liên quan:**
  * `mapADAS_4m/generate_aruco_markers.py` — Script sinh file PDF Marker
  * `lane_and_trafficsign/ADAS_STM32_Pi5/adas/app/config/map_config.py` — Bản đồ số
  * `lane_and_trafficsign/ADAS_STM32_Pi5/adas/app/perception/aruco_detector.py` — Nhận diện Marker
  * `lane_and_trafficsign/ADAS_STM32_Pi5/adas/app/decision/routing.py` — Thuật toán Dijkstra
  * `lane_and_trafficsign/ADAS_STM32_Pi5/adas/app/decision/fusion.py` — Tích hợp điều khiển

---

## Giai Đoạn 3: Xây dựng bối cảnh và Thu thập dữ liệu (Data Collection)
**Mục tiêu:** Thu thập dữ liệu hình ảnh thô để phục vụ cho việc huấn luyện mô hình YOLO nhận diện vật thể.
**Phân tích tin nhắn:** *"Xong rồi lấy data"* -> *"Thì mình làm mấy cái vật cản biển báo đồ á"* -> *"Khoảng cách các thứ"*

* **Công việc cụ thể:**
  1. **Bố trí Sa bàn:** Đặt các mô hình biển báo (Stop, Rẽ trái, Rẽ phải,...) và các vật cản (chướng ngại vật, xe giả lập) lên sa bàn.
  2. **Đa dạng hóa Khoảng cách:** ("Khoảng cách các thứ") Phải setup sao cho các biển báo/vật cản xuất hiện ở nhiều khoảng cách khác nhau (từ rất xa đến ngay trước mũi xe) và ở nhiều góc độ, điều kiện ánh sáng khác nhau để AI học được tính không gian.
  3. **Record Data:** Cho xe chạy rà qua các bối cảnh này và quay video hoặc chụp chuỗi frame ảnh liên tục lưu vào thẻ nhớ/máy tính.

---

## Giai Đoạn 4: Xử lý dữ liệu và Gán nhãn (Data Annotation)
**Mục tiêu:** Cung cấp "đáp án" cho mô hình AI học.
**Phân tích tin nhắn:** *"Xong label ảnh"*

* **Công việc cụ thể:**
  1. **Trích xuất Ảnh:** Cắt các video vừa quay ở Giai đoạn 3 thành các frame ảnh rời (ví dụ: 10 khung hình/giây). Lọc bỏ các ảnh mờ hoặc trùng lặp quá nhiều.
  2. **Gán nhãn (Labeling):** Sử dụng các công cụ như **Roboflow**, **CVAT**, hoặc **LabelImg**.
  3. Vẽ Bounding Box bao quanh các vật thể và gán cho chúng các nhãn tương ứng. Ví dụ các class: `stop_sign`, `turn_left`, `turn_right`, `obstacle`.

---

## Giai Đoạn 5: Xuất dữ liệu và Chuẩn bị Huấn luyện (Export Dataset)
**Mục tiêu:** Tạo bộ dữ liệu tương thích với chuẩn đầu vào của YOLO.
**Phân tích tin nhắn:** *"R xuất ra cái file yaml"*

* **Công việc cụ thể:**
  1. Từ phần mềm gán nhãn, cấu hình xuất dữ liệu (Export) theo định dạng **YOLO (YOLOv5, YOLOv8...)**.
  2. Hệ thống sẽ tự động sinh ra một file cấu hình quan trọng là `data.yaml` (chứa đường dẫn tới file ảnh train/val/test và danh sách các class) cùng với các file `.txt` chứa tọa độ Bounding Box cho từng ảnh.

---

## Giai Đoạn 6 (Mở rộng): Huấn luyện và Tích hợp Code
**Mục tiêu:** Đưa mô hình đã huấn luyện vào hoạt động thực tế trên Raspberry Pi 5.

* **Công việc cụ thể:**
  1. Đưa file `data.yaml` và thư mục ảnh lên Google Colab / Kaggle hoặc máy tính có GPU để tiến hành train YOLO.
  2. Export model weights ra định dạng `.onnx` hoặc `.pt`.
  3. Copy model mới vào thư mục `model/`.
  4. Cập nhật mã nguồn phần cứng và logic điều khiển:
     * Cập nhật danh sách class và cấu hình trong `sign_config.py`.
     * Tích hợp model mới vào `sign_detector.py`.
     * Thêm logic "Tránh vật cản" (Obstacle avoidance / Braking) vào `fusion.py` để ra quyết định giảm tốc/phanh dựa trên kích thước Bounding Box (tỷ lệ nghịch với khoảng cách) kết hợp với cảm biến siêu âm.
