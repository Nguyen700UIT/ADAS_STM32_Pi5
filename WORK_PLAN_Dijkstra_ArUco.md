# Kế Hoạch Triển Khai: Thuật Toán Dijkstra & ArUco Marker

Tài liệu này mô tả lộ trình và cấu trúc kiến trúc để tích hợp thuật toán tìm đường (Dijkstra) kết hợp định vị bằng ArUco Marker vào dự án ADAS_STM32_Pi5, bám sát các yêu cầu thực tế của phần cứng và sa hình.

## 1. Yêu Cầu Bài Toán (Từ Team Lead)

- **Đồ thị đầy đủ trọng số, vô hướng đi:** Xe di chuyển trên 1 làn, có thể đi 2 chiều. Trọng số là khoảng cách vật lý thực tế.
- **2 loại Node (ArUco):** 
  - *Node Hướng:* Đặt tại các ngã 3, ngã 4 để định vị ngã tư và quyết định hướng rẽ.
  - *Node Đích đến:* Đặt tại các bãi đỗ xe hoặc điểm kết thúc lộ trình.
- **Chỉ đường tại ngã tư:** Marker tại ngã tư kết hợp với bản đồ để biết cần Rẽ Trái, Rẽ Phải hay Đi Thẳng.
- **Trường hợp biên (Edge Case) - Không quay đầu xe:** Do góc cua hẹp trên 1 làn, hệ thống không được phép chỉ đường yêu cầu xe quay đầu 180 độ.

---

## 2. Kiến Trúc Tích Hợp Đề Xuất

Thay vì thay đổi luồng code cốt lõi, hệ thống sẽ được mở rộng bằng cách thêm các module chuyên biệt vào các tầng tương ứng trong thư mục `adas/app/`.

### 2.1. Tầng Cấu Hình (`config/map_config.py`)
**Mục đích:** Chứa bản đồ số (Đồ thị) của sa hình dưới dạng Hard-code.
- **Mapping:** Gán mỗi ID của ArUco với một vị trí trên sa hình.
- **Cấu trúc dữ liệu Đồ thị:** Lưu trữ dạng Dictionary. Chú ý phải lưu kèm **Hành động rẽ**.
  - *Ví dụ:* `Node_1` -> `Node_2` (Khoảng cách: 20cm, Hành động: `STRAIGHT`)

### 2.2. Tầng Nhận Diện (`perception/aruco_detector.py`)
**Mục đích:** Trích xuất thông tin Marker từ camera (chạy song song/độc lập với YOLO).
- Sử dụng thư viện `cv2.aruco`.
- Hàm chính sẽ liên tục quét khung hình, nếu phát hiện Marker sẽ trả về `Marker_ID` và `Khoảng cách` (ước lượng) để chuẩn bị đánh lái.

### 2.3. Tầng Thuật Toán Tìm Đường (`decision/routing.py`)
**Mục đích:** Tìm đường đi ngắn nhất từ Điểm Xuất Phát đến Đích.
- **State-based Dijkstra (Dijkstra theo trạng thái):** Thuật toán Dijkstra sẽ được tinh chỉnh. Thay vì duyệt qua từng Đỉnh (Node), thuật toán duyệt qua trạng thái `(Node_Trước, Node_Hiện_Tại)` để tính khoảng cách tới `(Node_Hiện_Tại, Node_Kế_Tiếp)`.
- **Xử lý Không Quay Đầu:** Nếu `Node_Kế_Tiếp` trùng với `Node_Trước`, trọng số sẽ được thiết lập là $\infty$ (Vô cực), ép xe phải tìm đường đi vòng (ví dụ qua bùng binh) thay vì quay đầu xe tại chỗ.

### 2.4. Tầng Điều Phối & Quyết Định (`decision/fusion.py` - Cập nhật)
**Mục đích:** Kết hợp thuật toán bám làn (Lane Keeping) với Định tuyến (Routing).
**Luồng hoạt động:**
1. Khởi tạo xe, tính toán lộ trình (VD: `ID 1 -> ID 3 -> ID 5`).
2. Xe di chuyển bằng module `lane_controller.py` (Bám vạch).
3. Khi `aruco_detector` bắt được Marker `ID 3`:
   - Tra lộ trình: Bước tiếp theo là đến `ID 5`.
   - Tra bản đồ (`map_config`): Từ `ID 3` sang `ID 5` là lệnh **TURN_LEFT**.
   - Ép góc vô lăng bẻ sang trái trong 1 khoảng thời gian/khoảng cách nhất định để qua ngã tư.
4. Trả lại quyền điều khiển cho `lane_controller` bám vạch.
5. Gặp Marker Đích -> Gửi lệnh phanh (Brake) qua UART.

---

## 3. Hướng Dẫn Setup Vật Lý (Thiết Kế Sa Hình)

Để camera trên xe Pi nhận diện chuẩn xác nhất, khâu dán Marker thực tế cực kỳ quan trọng:

1. **Vị trí dán tại Ngã Tư:**
   - **KHÔNG dán Marker ở chính giữa tâm ngã tư.** Camera xe có góc nhìn thấp, khi tới giữa ngã tư sẽ bị mất dấu (Góc mù).
   - **NÊN dán Marker ở nhánh đường vào ngã tư** (cách tâm khoảng 10-15cm). Xe sẽ nhận diện sớm, tra lộ trình và chuẩn bị bẻ lái kịp thời.

2. **Quy tắc 4 Marker cho 1 Ngã 4:**
   - Mỗi ngã tư nên dán Marker cho từng hướng tiếp cận riêng biệt (Bắc, Nam, Đông, Tây vào ngã 4 đó sẽ là 4 ID Marker khác nhau). 
   - Lý do: Xe cần biết chính xác đầu xe đang đối diện với ngã tư từ hướng nào để áp dụng góc rẽ tương ứng từ `map_config`.

3. **Kích thước Marker:**
   - In kích thước vừa phải (VD: 3x3 cm hoặc 5x5 cm tùy độ cao camera), đủ để đọc từ xa nhưng không quá to để tránh làm nhiễu thuật toán phát hiện viền làn đường.

---

## 4. Các Bước Triển Khai (Roadmap)

- [ ] **Bước 1:** Khảo sát sa hình, lập bản đồ (Ghi chú ID ngã tư, đo khoảng cách, xác định hướng rẽ trái/phải).
- [ ] **Bước 2:** Code `config/map_config.py` để biểu diễn đồ thị từ bản khảo sát.
- [ ] **Bước 3:** Code `perception/aruco_detector.py` và test nhận diện bằng Camera Pi.
- [ ] **Bước 4:** Code `decision/routing.py` (Thuật toán State-based Dijkstra). Test thử logic trên Terminal (không cần xe).
- [ ] **Bước 5:** Tích hợp vào `decision/fusion.py`.
- [ ] **Bước 6:** Chạy thực tế nghiệm thu.
