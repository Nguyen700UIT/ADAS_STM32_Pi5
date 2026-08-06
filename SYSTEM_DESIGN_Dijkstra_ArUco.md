# Kiến Trúc Hệ Thống Dẫn Đường Tự Động (Dijkstra + ArUco)

Tài liệu này là bản tổng hợp hoàn chỉnh, giải thích chi tiết mục đích của từng file code trong hệ thống và cách xây dựng sự kết hợp hoàn hảo giữa Thuật toán Tìm đường (Dijkstra) và Hệ thống Định vị (ArUco Marker).

---

## 1. Mối Liên Hệ Giữa Dijkstra và ArUco

Hệ thống dẫn đường tự động bắt buộc phải có sự kết hợp của hai thành phần này để hoạt động:
- **ArUco Marker (Đôi Mắt):** Đóng vai trò định vị (Localization). Nó cho chiếc xe biết chính xác nó đang đứng ở ngã tư nào trên sa bàn thực tế.
- **Dijkstra (Bộ Não):** Đóng vai trò vạch lộ trình (Routing). Nó cầm tấm bản đồ, nhận vị trí từ "Đôi Mắt", sau đó tính toán xem để đi đến đích thì xe phải rẽ hướng nào.

---

## 2. Mục Đích & Chức Năng Các File Code Đã Tạo

Toàn bộ hệ thống được chia làm 3 file code độc lập theo chuẩn thiết kế module hóa:

### 2.1. Tầng Dữ Liệu: `config/map_config.py`
**Mục đích:** Đóng vai trò là "Bản đồ Google Maps" thu nhỏ của chiếc xe. Nó số hóa bức ảnh sa bàn thực tế thành các con số mà máy tính hiểu được.
- **Chứa `GRAPH` (Đồ thị):** Lưu khoảng cách vật lý thực tế giữa các ngã tư với nhau. Thuật toán Dijkstra sẽ đọc cái này để tìm đường đi ngắn nhất.
- **Chứa `ACTION_MAP` (Bảng Hành Động):** Đây là "từ điển rẽ". Nó định nghĩa quy tắc: Nếu xe đi từ A (Prev), tới ngã tư B (Curr), và muốn sang ngã tư C (Next) thì phải rẽ Trái hay Phải.
- **Quy hoạch ID:** Quy ước gán cứng ID từ `1-49` cho ngã tư, và `50-99` cho điểm đỗ xe.

### 2.2. Tầng Nhận Diện: `perception/aruco_detector.py`
**Mục đích:** Cung cấp "Thị giác" cho xe.
- Nhiệm vụ duy nhất của file này là xử lý ảnh từ Camera Pi để **đọc ra con số ID của Marker** nằm trên đường.
- **Cách xây dựng:** Code được viết tối giản nhất có thể (chỉ dùng `detectMarkers` của OpenCV). Nó cố tình KHÔNG đo đạc các góc 3D phức tạp (Pose Estimation) để tiết kiệm tài nguyên vi xử lý trên Raspberry Pi và chống nhiễu loạn khi xe rung lắc.

### 2.3. Tầng Thuật Toán: `decision/routing.py`
**Mục đích:** Tính toán lộ trình thông minh và chặn các hành vi lái xe nguy hiểm.
- **Cách xây dựng (State-based Dijkstra):** Đây không phải là thuật toán Dijkstra thông thường. File này được thiết kế để nhớ được "Trạng thái" của xe (xe vừa đi qua ngã tư nào).
- **Tính năng chặn Quay đầu (U-Turn):** Do sa bàn chỉ có 1 làn đường, xe không thể quay đầu. File này chứa logic: Nếu phát hiện con đường ngắn nhất yêu cầu xe phải đi ngược lại ngã tư vừa đi qua, nó sẽ lập tức gán khoảng cách của con đường đó bằng Vô Cực ($\infty$), ép chiếc xe phải tìm một con đường vòng khác.

---

## 3. Cách Xây Dựng & Bố Trí Thực Tế Trên Sa Bàn

Để 3 file code trên chạy mượt mà, khâu thi công dán Marker vật lý phải tuân thủ nghiêm ngặt các quy tắc sau:

### 3.1. Thiết Kế ArUco Marker
- **Chuẩn In:** In các hình vuông đen trắng theo chuẩn `DICT_4X4_100` (vì nó chứa ít bit, các ô vuông to, camera dễ đọc từ xa).
- **Kích thước:** Khoảng 4x4 cm đến 5x5 cm.

### 3.2. Chiến Thuật Dán Marker (Chỉ 1 Marker / Ngã Tư)
- Nhờ sự thông minh của bảng `ACTION_MAP` trong `map_config.py`, xe đã tự biết nó đến từ hướng nào dựa vào trí nhớ. Do đó, ta **KHÔNG CẦN** dán 4 marker ở 4 hướng của ngã tư.
- **Chỉ dán ĐÚNG 1 Marker duy nhất** cho mỗi ngã tư. 
- **Vị trí dán:** Không dán ở ngay tâm ngã tư (vì đầu xe che khuất). Phải dán ở lề ngã tư hoặc lệch về hướng xe hay đi tới, sao cho camera nhìn thấy Marker khi xe còn cách ngã tư 15-20cm.

---

## 4. Tóm Tắt Kịch Bản Tích Hợp (Tương lai - File `fusion.py`)

Khi toàn bộ hệ thống được kích hoạt, kịch bản phối hợp sẽ diễn ra như sau:
1. Xe bám vạch kẻ đường chạy bình thường.
2. `aruco_detector.py` (Mắt) nhìn thấy Marker ID số 5.
3. `fusion.py` nhớ lại: "Mình vừa đi qua số 2".
4. Nó hỏi `routing.py` (Não): "Từ 2 đến 5, đích là 51 thì đi đâu?". `routing.py` trả lời: "Đi sang 8, lệnh là TURN_LEFT".
5. `fusion.py` lập tức ra lệnh cho vô lăng: "Chỉ bám theo vạch cong bên trái!". Xe lượn qua ngã tư hoàn hảo. 
6. Gặp Marker ID >= 50, phanh xe. Hành trình kết thúc!
