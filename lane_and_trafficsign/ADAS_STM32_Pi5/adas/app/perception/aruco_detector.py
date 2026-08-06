# =============================================================================
# ArUco Marker Detector – Tầng Nhận Diện ArUco
# =============================================================================
# Module này CHỈ LÀM 1 VIỆC DUY NHẤT: Phát hiện ID của ArUco Marker
# trong khung hình camera. Không tính Pose / góc 3D.
#
# Thiết kế tối giản nhất có thể để đảm bảo:
#   - Chạy nhanh (realtime trên Raspberry Pi)
#   - Ổn định (không bị nhiễu bởi rung lắc)
#   - Dễ debug (chỉ trả về ID, không có thêm dữ liệu thừa)
# =============================================================================

import cv2 as cv


class ArucoDetector:
    """Phát hiện ArUco Marker trong khung hình camera.

    Attributes
    ----------
    aruco_dict : cv2.aruco.Dictionary
        Bộ từ điển ArUco được sử dụng (mặc định DICT_4X4_100).
    detector_params : cv2.aruco.DetectorParameters
        Tham số cấu hình cho bộ dò ArUco.

    Usage
    -----
    >>> detector = ArucoDetector()
    >>> ids = detector.detect(frame)
    >>> if ids:
    ...     print(f"Nhìn thấy Marker: {ids}")
    """

    def __init__(self, dictionary_id=cv.aruco.DICT_4X4_100):
        """Khởi tạo bộ dò ArUco.

        Parameters
        ----------
        dictionary_id : int, optional
            Loại từ điển ArUco. Mặc định là ``DICT_4X4_100``
            (100 marker với lưới 4x4 bit — phù hợp cho xe nhỏ,
            in kích thước 3-5cm vẫn đọc tốt).
        """
        self.aruco_dict = cv.aruco.getPredefinedDictionary(dictionary_id)
        self.detector_params = cv.aruco.DetectorParameters()

        # Tăng khả năng nhận diện trong điều kiện sáng yếu / mờ
        self.detector_params.adaptiveThreshWinSizeMin = 3
        self.detector_params.adaptiveThreshWinSizeMax = 23
        self.detector_params.adaptiveThreshWinSizeStep = 10
        self.detector_params.minMarkerPerimeterRate = 0.03
        self.detector_params.maxMarkerPerimeterRate = 4.0

        self._detector = cv.aruco.ArucoDetector(
            self.aruco_dict, self.detector_params
        )

    def detect(self, frame):
        """Quét khung hình và trả về danh sách ID các Marker phát hiện được.

        Parameters
        ----------
        frame : numpy.ndarray
            Khung hình BGR từ camera (hoặc video).

        Returns
        -------
        list[int]
            Danh sách các ID Marker được phát hiện (có thể rỗng).
            Đã loại bỏ trùng lặp và sắp xếp tăng dần.
        """
        # Chuyển sang ảnh xám để tăng tốc xử lý
        if len(frame.shape) == 3:
            gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        else:
            gray = frame

        corners, ids, _rejected = self._detector.detectMarkers(gray)

        if ids is None:
            return []

        # Trả về danh sách ID duy nhất, sắp xếp tăng dần
        detected_ids = sorted(set(int(marker_id) for marker_id in ids.flatten()))
        return detected_ids

    def detect_first(self, frame):
        """Quét khung hình và trả về ID của Marker ĐẦU TIÊN phát hiện được.

        Hàm tiện ích khi xe chỉ kỳ vọng nhìn thấy 1 Marker tại một thời điểm.

        Parameters
        ----------
        frame : numpy.ndarray
            Khung hình BGR từ camera.

        Returns
        -------
        int or None
            ID của Marker đầu tiên, hoặc ``None`` nếu không phát hiện.
        """
        ids = self.detect(frame)
        return ids[0] if ids else None

    def draw_markers(self, frame):
        """Vẽ Bounding Box và ID lên khung hình (dành cho Debug / Hiển thị).

        Parameters
        ----------
        frame : numpy.ndarray
            Khung hình BGR gốc.

        Returns
        -------
        numpy.ndarray
            Bản sao khung hình đã được vẽ bounding box và ID marker.
        list[int]
            Danh sách ID phát hiện được (có thể rỗng).
        """
        output = frame.copy()

        if len(frame.shape) == 3:
            gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        else:
            gray = frame

        corners, ids, _rejected = self._detector.detectMarkers(gray)

        if ids is not None and len(corners) > 0:
            cv.aruco.drawDetectedMarkers(output, corners, ids)

        detected_ids = []
        if ids is not None:
            detected_ids = sorted(set(int(mid) for mid in ids.flatten()))

        return output, detected_ids
