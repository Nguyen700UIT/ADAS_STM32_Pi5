from enum import Enum

try:
    from ..config import sign_config as cfg
    from ..config import map_config
except ImportError:
    from config import sign_config as cfg
    from config import map_config

from perception.aruco_detector import ArucoDetector
from decision.routing import RoutingEngine


class FusionState(Enum):
    """Operating states for the ADAS fusion controller."""
    LANE_FOLLOWING = "lane_following"
    TURNING_LEFT = "turning_left"
    TURNING_RIGHT = "turning_right"
    STOPPED = "stopped"


class FusionController:
    """State machine that coordinates Lane, Sign, Dijkstra and ArUco.

    Có 2 chế độ hoạt động:
    - **Chế độ Biển báo (Sign-based):** Rẽ dựa trên biển báo giao thông
      (giữ nguyên logic cũ).
    - **Chế độ Dẫn đường (Navigation):** Khi có đích đến (goal_node),
      hệ thống sử dụng ArUco + Dijkstra để tự động tính lộ trình và
      ra lệnh rẽ tại mỗi ngã tư.

    Kịch bản tích hợp (Mục 4 - SYSTEM_DESIGN):
    1. Xe bám vạch kẻ đường chạy bình thường.
    2. aruco_detector nhìn thấy Marker ID (ví dụ: 5).
    3. fusion nhớ lại: "Mình vừa đi qua Node 2".
    4. Nó hỏi routing: "Từ 2 đến 5, đích là 51 thì đi đâu?"
       → routing trả lời: "Đi sang 8, lệnh là TURN_LEFT".
    5. fusion ra lệnh cho vô lăng bẻ trái.
    6. Gặp Marker ID >= 50 và trùng đích → phanh xe.
    """

    def __init__(self, lane_controller, sign_controller):
        """
        Parameters
        ----------
        lane_controller : LaneController
            Handles lane-following UART commands.
        sign_controller : SignController
            Handles sign-action UART commands (turn / stop).
        """
        self.lane_ctrl = lane_controller
        self.sign_ctrl = sign_controller
        self.state = FusionState.LANE_FOLLOWING

        # ---- Dijkstra + ArUco components ----
        self.aruco_detector = ArucoDetector()
        self.router = RoutingEngine()

        # ---- Navigation state ----
        self.goal_node = None       # Đích đến (None = chế độ biển báo)
        self.prev_node = None       # Node trước đó
        self.curr_node = None       # Node hiện tại
        self.path = []              # Lộ trình đầy đủ [start, ..., goal]
        self.path_index = 0         # Vị trí hiện tại trong lộ trình
        self.last_seen_marker = None  # Marker ID gần nhất đã xử lý
        self.navigation_active = False  # Đang trong chế độ dẫn đường?
        self.arrived = False        # Đã đến đích?

    # ------------------------------------------------------------------
    # Navigation API
    # ------------------------------------------------------------------
    def set_destination(self, goal_node, start_node=None):
        """Thiết lập đích đến để kích hoạt chế độ dẫn đường Dijkstra.

        Parameters
        ----------
        goal_node : int
            ID Node đích đến (thường >= 50).
        start_node : int or None
            ID Node xuất phát. Nếu None, chờ ArUco nhận diện Node đầu tiên.
        """
        self.goal_node = goal_node
        self.arrived = False

        if start_node is not None:
            path, cost = self.router.find_path(start=start_node, goal=goal_node)
            if path:
                self.path = path
                self.path_index = 0
                self.prev_node = None
                self.curr_node = start_node
                self.navigation_active = True
                print(f"[NAV] 🗺️ Lộ trình: {' → '.join(map(str, path))}")
                print(f"[NAV] 📏 Tổng khoảng cách: {cost} cm")
            else:
                print(f"[NAV] ❌ Không tìm được đường từ {start_node} đến {goal_node}!")
                self.navigation_active = False
        else:
            # Chờ ArUco phát hiện Node đầu tiên
            self.navigation_active = True
            self.path = []
            self.path_index = 0
            self.prev_node = None
            self.curr_node = None
            print(f"[NAV] 🎯 Đích đến: {goal_node}. Đang chờ ArUco phát hiện vị trí hiện tại...")

    def cancel_navigation(self):
        """Hủy chế độ dẫn đường, quay về chế độ biển báo."""
        self.goal_node = None
        self.navigation_active = False
        self.path = []
        self.path_index = 0
        self.prev_node = None
        self.curr_node = None
        self.arrived = False
        self.last_seen_marker = None
        self.state = FusionState.LANE_FOLLOWING
        print("[NAV] ❎ Đã hủy dẫn đường.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def update(self, detected_signs, left_fit, right_fit,
               center_fitx, ploty, lane_valid, frame=None):
        """Run one decision cycle.

        Parameters
        ----------
        detected_signs : list[str]
            Sign class names returned by SignDetector.
        left_fit, right_fit, center_fitx, ploty :
            Lane detection outputs forwarded to LaneController.
        lane_valid : bool
            Whether a lane was successfully detected this frame.
        frame : numpy.ndarray or None
            Khung hình BGR từ camera, dùng để quét ArUco (chế độ dẫn đường).

        Returns
        -------
        dict
            Status information for logging / debugging.
        """
        # ==============================================================
        # CHẾ ĐỘ DẪN ĐƯỜNG (Dijkstra + ArUco)
        # ==============================================================
        if self.navigation_active and frame is not None:
            return self._update_navigation(
                frame, detected_signs,
                left_fit, right_fit, center_fitx, ploty, lane_valid
            )

        # ==============================================================
        # CHẾ ĐỘ BIỂN BÁO (Logic cũ - giữ nguyên)
        # ==============================================================
        return self._update_sign_based(
            detected_signs, left_fit, right_fit, center_fitx, ploty, lane_valid
        )

    # ------------------------------------------------------------------
    # Navigation Mode (Dijkstra + ArUco)
    # ------------------------------------------------------------------
    def _update_navigation(self, frame, detected_signs,
                           left_fit, right_fit, center_fitx, ploty, lane_valid):
        """Xử lý 1 frame trong chế độ dẫn đường."""

        # 1. Quét ArUco trong khung hình
        marker_ids = self.aruco_detector.detect(frame)

        # 2. Nếu phát hiện Marker mới
        if marker_ids:
            marker_id = marker_ids[0]  # Lấy marker đầu tiên

            # Chỉ xử lý nếu đây là marker MỚI (tránh xử lý lặp lại cùng 1 marker)
            if marker_id != self.last_seen_marker:
                self.last_seen_marker = marker_id
                return self._process_new_marker(
                    marker_id, detected_signs,
                    left_fit, right_fit, center_fitx, ploty, lane_valid
                )

        # 3. Không có marker mới → tiếp tục hành động hiện tại
        return self._continue_current_action(
            detected_signs, left_fit, right_fit, center_fitx, ploty, lane_valid
        )

    def _process_new_marker(self, marker_id, detected_signs,
                            left_fit, right_fit, center_fitx, ploty, lane_valid):
        """Xử lý khi phát hiện một ArUco Marker mới."""

        print(f"[NAV] 👁️ Nhìn thấy Marker ID: {marker_id}")

        # ---- Trường hợp đặc biệt: Marker là đích đến ----
        if marker_id == self.goal_node:
            self.arrived = True
            self.state = FusionState.STOPPED
            self.sign_ctrl.execute_stop()
            print(f"[NAV] 🏁 ĐÃ ĐẾN ĐÍCH! (Node {marker_id})")
            return self._status(
                f"🏁 ĐÃ ĐẾN ĐÍCH Node {marker_id}",
                nav_info=self._nav_info(marker_id=marker_id, action="STOP")
            )

        # ---- Marker là Node Đích khác (đi ngang qua, chưa phải đích) ----
        if map_config.is_destination_node(marker_id) and marker_id != self.goal_node:
            print(f"[NAV] 🏪 Đi ngang qua điểm đỗ {marker_id} (không phải đích)")

        # ---- Lần đầu phát hiện vị trí (chưa biết mình ở đâu) ----
        if self.curr_node is None:
            self.curr_node = marker_id
            # Tính lộ trình từ vị trí hiện tại
            path, cost = self.router.find_path(start=marker_id, goal=self.goal_node)
            if path:
                self.path = path
                self.path_index = 0
                print(f"[NAV] 🗺️ Lộ trình: {' → '.join(map(str, path))}")
                print(f"[NAV] 📏 Tổng khoảng cách: {cost} cm")
            else:
                print(f"[NAV] ❌ Không tìm được đường từ {marker_id} đến {self.goal_node}!")
            # Tiếp tục bám làn chờ marker tiếp theo
            return self._do_lane_following(left_fit, right_fit, center_fitx, ploty, lane_valid,
                                           f"Khởi đầu tại Node {marker_id}")

        # ---- Đã biết vị trí → Cập nhật và ra lệnh rẽ ----
        self.prev_node = self.curr_node
        self.curr_node = marker_id

        # Tính lại lộ trình từ vị trí hiện tại (có nhớ prev_node để chặn U-Turn)
        path, cost = self.router.find_path(
            start=marker_id,
            goal=self.goal_node,
            initial_prev=self.prev_node
        )

        if not path or len(path) < 2:
            print(f"[NAV] ⚠️ Không tìm được đường tiếp từ Node {marker_id}!")
            return self._do_lane_following(left_fit, right_fit, center_fitx, ploty, lane_valid,
                                           f"⚠️ Mất lộ trình tại Node {marker_id}")

        self.path = path
        self.path_index = 0
        next_node = path[1]  # Node kế tiếp trong lộ trình

        # Tra bảng ACTION_MAP để lấy hành động rẽ
        try:
            action = self.router.get_next_action(self.prev_node, marker_id, next_node)
            action_str = action.value  # "straight" / "turn_left" / "turn_right"
            print(f"[NAV] 🧠 Từ {self.prev_node} → tại {marker_id} → sang {next_node}: {action_str.upper()}")

            return self._execute_turn_action(
                action_str, left_fit, right_fit, center_fitx, ploty, lane_valid,
                marker_id, next_node
            )
        except KeyError:
            print(f"[NAV] ⚠️ Không tìm thấy ACTION cho ({self.prev_node}, {marker_id}, {next_node})")
            return self._do_lane_following(left_fit, right_fit, center_fitx, ploty, lane_valid,
                                           f"⚠️ Thiếu ACTION ({self.prev_node},{marker_id},{next_node})")

    def _execute_turn_action(self, action_str, left_fit, right_fit,
                             center_fitx, ploty, lane_valid, marker_id, next_node):
        """Thực thi lệnh rẽ dựa trên kết quả Dijkstra."""
        if action_str == "turn_left":
            self.state = FusionState.TURNING_LEFT
            self.sign_ctrl.execute_turn_left()
            return self._status(
                f"NAV: TURN_LEFT tại Node {marker_id} → {next_node}",
                nav_info=self._nav_info(marker_id=marker_id, action="TURN_LEFT", next_node=next_node)
            )
        elif action_str == "turn_right":
            self.state = FusionState.TURNING_RIGHT
            self.sign_ctrl.execute_turn_right()
            return self._status(
                f"NAV: TURN_RIGHT tại Node {marker_id} → {next_node}",
                nav_info=self._nav_info(marker_id=marker_id, action="TURN_RIGHT", next_node=next_node)
            )
        else:
            # STRAIGHT → tiếp tục bám làn
            self.state = FusionState.LANE_FOLLOWING
            lane_result = self.lane_ctrl.update(
                left_fit, right_fit, center_fitx, ploty, lane_valid
            )
            return self._status(
                f"NAV: STRAIGHT tại Node {marker_id} → {next_node}",
                lane_result=lane_result,
                nav_info=self._nav_info(marker_id=marker_id, action="STRAIGHT", next_node=next_node)
            )

    def _continue_current_action(self, detected_signs,
                                  left_fit, right_fit, center_fitx, ploty, lane_valid):
        """Tiếp tục hành động hiện tại khi không có marker mới."""

        if self.arrived:
            self.sign_ctrl.execute_stop()
            return self._status("🏁 Đã đến đích - xe đang dừng",
                                nav_info=self._nav_info(action="STOP"))

        # TURNING_LEFT: Chờ biển biến mất + có làn → quay về bám làn
        if self.state == FusionState.TURNING_LEFT:
            if lane_valid:
                self.state = FusionState.LANE_FOLLOWING
                lane_result = self.lane_ctrl.update(
                    left_fit, right_fit, center_fitx, ploty, lane_valid
                )
                return self._status("NAV: Rẽ trái xong → LANE_FOLLOWING",
                                    lane_result=lane_result,
                                    nav_info=self._nav_info())
            self.sign_ctrl.execute_turn_left()
            return self._status("NAV: Đang rẽ trái...",
                                nav_info=self._nav_info(action="TURN_LEFT"))

        # TURNING_RIGHT: tương tự
        if self.state == FusionState.TURNING_RIGHT:
            if lane_valid:
                self.state = FusionState.LANE_FOLLOWING
                lane_result = self.lane_ctrl.update(
                    left_fit, right_fit, center_fitx, ploty, lane_valid
                )
                return self._status("NAV: Rẽ phải xong → LANE_FOLLOWING",
                                    lane_result=lane_result,
                                    nav_info=self._nav_info())
            self.sign_ctrl.execute_turn_right()
            return self._status("NAV: Đang rẽ phải...",
                                nav_info=self._nav_info(action="TURN_RIGHT"))

        # LANE_FOLLOWING: Bám làn bình thường
        lane_result = self.lane_ctrl.update(
            left_fit, right_fit, center_fitx, ploty, lane_valid
        )
        return self._status("NAV: Bám làn → chờ ArUco tiếp theo",
                            lane_result=lane_result,
                            nav_info=self._nav_info())

    def _do_lane_following(self, left_fit, right_fit, center_fitx, ploty, lane_valid, message):
        """Helper: Thực hiện bám làn kèm thông báo."""
        self.state = FusionState.LANE_FOLLOWING
        lane_result = self.lane_ctrl.update(
            left_fit, right_fit, center_fitx, ploty, lane_valid
        )
        return self._status(message, lane_result=lane_result, nav_info=self._nav_info())

    # ------------------------------------------------------------------
    # Sign-based Mode (Logic cũ - giữ nguyên 100%)
    # ------------------------------------------------------------------
    def _update_sign_based(self, detected_signs,
                           left_fit, right_fit, center_fitx, ploty, lane_valid):
        """Xử lý dựa trên biển báo giao thông (chế độ mặc định)."""

        has_stop = cfg.CLASS_STOP in detected_signs
        has_left = cfg.CLASS_TURN_LEFT in detected_signs
        has_right = cfg.CLASS_TURN_RIGHT in detected_signs

        # ----- LANE_FOLLOWING state -----
        if self.state == FusionState.LANE_FOLLOWING:
            if has_stop:
                self.state = FusionState.STOPPED
                self.sign_ctrl.execute_stop()
                return self._status("stop sign detected → STOPPED")

            if has_left:
                self.state = FusionState.TURNING_LEFT
                self.sign_ctrl.execute_turn_left()
                return self._status("turn_left sign detected → TURNING_LEFT")

            if has_right:
                self.state = FusionState.TURNING_RIGHT
                self.sign_ctrl.execute_turn_right()
                return self._status("turn_right sign detected → TURNING_RIGHT")

            lane_result = self.lane_ctrl.update(
                left_fit, right_fit, center_fitx, ploty, lane_valid
            )
            return self._status("lane following", lane_result=lane_result)

        # ----- STOPPED state -----
        if self.state == FusionState.STOPPED:
            if has_stop:
                self.sign_ctrl.execute_stop()
                return self._status("stop sign still visible — holding stop")

            self.state = FusionState.LANE_FOLLOWING
            lane_result = self.lane_ctrl.update(
                left_fit, right_fit, center_fitx, ploty, lane_valid
            )
            return self._status(
                "stop sign gone → LANE_FOLLOWING", lane_result=lane_result
            )

        # ----- TURNING_LEFT state -----
        if self.state == FusionState.TURNING_LEFT:
            if not has_left and lane_valid:
                self.state = FusionState.LANE_FOLLOWING
                lane_result = self.lane_ctrl.update(
                    left_fit, right_fit, center_fitx, ploty, lane_valid
                )
                return self._status(
                    "turn_left sign gone + lane valid → LANE_FOLLOWING",
                    lane_result=lane_result,
                )

            self.sign_ctrl.execute_turn_left()
            return self._status("turning left — waiting for sign gone + lane")

        # ----- TURNING_RIGHT state -----
        if self.state == FusionState.TURNING_RIGHT:
            if not has_right and lane_valid:
                self.state = FusionState.LANE_FOLLOWING
                lane_result = self.lane_ctrl.update(
                    left_fit, right_fit, center_fitx, ploty, lane_valid
                )
                return self._status(
                    "turn_right sign gone + lane valid → LANE_FOLLOWING",
                    lane_result=lane_result,
                )

            self.sign_ctrl.execute_turn_right()
            return self._status("turning right — waiting for sign gone + lane")

        # Fallback
        return self._status("unknown state")

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------
    def reset(self):
        """Reset the fusion controller to its initial state."""
        self.state = FusionState.LANE_FOLLOWING
        self.lane_ctrl.reset()
        self.cancel_navigation()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _nav_info(self, marker_id=None, action=None, next_node=None):
        """Tạo dict thông tin navigation cho Web Dashboard."""
        return {
            "goal": self.goal_node,
            "prev_node": self.prev_node,
            "curr_node": self.curr_node,
            "marker_id": marker_id,
            "action": action,
            "next_node": next_node,
            "path": self.path,
            "arrived": self.arrived,
        }

    def _status(self, message, lane_result=None, nav_info=None):
        return {
            "state": self.state.value,
            "message": message,
            "lane_result": lane_result,
            "nav_info": nav_info,
        }
