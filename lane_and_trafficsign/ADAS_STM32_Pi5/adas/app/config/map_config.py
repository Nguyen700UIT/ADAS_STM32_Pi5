# =============================================================================
# Map Configuration – Bản đồ số của sa hình ADAS
# =============================================================================
# File này chứa toàn bộ thông tin Đồ thị (Graph) đã được "phiên dịch"
# từ ảnh chụp sa hình (mapADAS_4m) sang cấu trúc dữ liệu Python.
#
# *** HƯỚNG DẪN SỬ DỤNG ***
# 1. Khảo sát sa hình thật, đo khoảng cách giữa các ngã tư / bãi đỗ.
# 2. Dán ArUco Marker lên sa hình và ghi chú ID.
# 3. Thay dữ liệu DEMO bên dưới bằng dữ liệu thực tế.
# =============================================================================

from enum import Enum


# ---- Hành Động Khi Qua Ngã Tư ----
class TurnAction(Enum):
    """Các hành động xe có thể thực hiện tại ngã tư."""
    STRAIGHT = "straight"       # Đi thẳng
    TURN_LEFT = "turn_left"     # Rẽ trái
    TURN_RIGHT = "turn_right"   # Rẽ phải


# ---- Phân Loại Node ----
# Quy ước: ID 1-49 = Node Hướng (Ngã tư), ID 50-99 = Node Đích (Bãi đỗ)
DIRECTION_NODE_MAX_ID = 49      # ID <= 49 là ngã tư
DESTINATION_NODE_MIN_ID = 50    # ID >= 50 là đích đến


def is_destination_node(node_id: int) -> bool:
    """Kiểm tra node này có phải là đích đến hay không."""
    return node_id >= DESTINATION_NODE_MIN_ID


def is_direction_node(node_id: int) -> bool:
    """Kiểm tra node này có phải là ngã tư hay không."""
    return 1 <= node_id <= DIRECTION_NODE_MAX_ID


# =============================================================================
# ĐỒ THỊ – Adjacency List (Danh sách kề)
# =============================================================================
# Key: node_id
# Value: dict {neighbor_id: weight (khoảng cách thực tế tính bằng cm)}
#
# Đồ thị VÔ HƯỚNG: Mỗi cạnh phải được khai báo ở CẢ HAI phía.
#
# *** DỮ LIỆU DEMO – Thay bằng dữ liệu thực tế sau khi đo sa hình ***
# Sơ đồ demo mô tả bản đồ sa hình dạng lưới đơn giản:
#
#   [1] ---30cm--- [2] ---25cm--- [3]
#    |              |              |
#   35cm          40cm           35cm
#    |              |              |
#   [4] ---30cm--- [5] ---25cm--- [6]
#    |              |              |
#   30cm          30cm           30cm
#    |              |              |
#  [50] ---25cm--- [7] ---25cm--- [51]
#
# Node 1-7: Ngã tư (Node Hướng)
# Node 50, 51: Bãi đỗ xe (Node Đích)
# =============================================================================

GRAPH = {
    # ---- Node Hướng (Ngã tư) ----
    1:  {2: 30, 4: 35},
    2:  {1: 30, 3: 25, 5: 40},
    3:  {2: 25, 6: 35},
    4:  {1: 35, 5: 30, 50: 30},
    5:  {2: 40, 4: 30, 6: 25, 7: 30},
    6:  {3: 35, 5: 25, 51: 30},
    7:  {5: 30, 50: 25, 51: 25},

    # ---- Node Đích (Bãi đỗ xe) ----
    50: {4: 30, 7: 25},
    51: {6: 30, 7: 25},
}


# =============================================================================
# BẢNG HÀNH ĐỘNG – Action Map
# =============================================================================
# Key: (prev_node, curr_node, next_node)
# Value: TurnAction
#
# Đây là "bộ não" giúp xe biết cần rẽ hướng nào tại ngã tư
# mà chỉ cần nhìn thấy 1 ArUco Marker duy nhất.
#
# Cách điền: Đứng tại ngã tư curr_node, đã đi tới từ prev_node,
# muốn đi tiếp sang next_node thì phải thực hiện hành động gì?
#
# *** DỮ LIỆU DEMO – Thay bằng dữ liệu thực tế sau khi đo sa hình ***
# =============================================================================

ACTION_MAP = {
    # ---- Ngã tư 1 (T-junction: nối 2, 4) ----
    (2, 1, 4):  TurnAction.TURN_RIGHT,
    (4, 1, 2):  TurnAction.TURN_LEFT,

    # ---- Ngã tư 2 (Cross: nối 1, 3, 5) ----
    (1, 2, 3):  TurnAction.STRAIGHT,
    (1, 2, 5):  TurnAction.TURN_RIGHT,
    (3, 2, 1):  TurnAction.STRAIGHT,
    (3, 2, 5):  TurnAction.TURN_LEFT,
    (5, 2, 1):  TurnAction.TURN_LEFT,
    (5, 2, 3):  TurnAction.TURN_RIGHT,

    # ---- Ngã tư 3 (T-junction: nối 2, 6) ----
    (2, 3, 6):  TurnAction.TURN_RIGHT,
    (6, 3, 2):  TurnAction.TURN_LEFT,

    # ---- Ngã tư 4 (T-junction: nối 1, 5, 50) ----
    (1, 4, 5):   TurnAction.STRAIGHT,
    (1, 4, 50):  TurnAction.TURN_RIGHT,
    (5, 4, 1):   TurnAction.STRAIGHT,
    (5, 4, 50):  TurnAction.TURN_LEFT,
    (50, 4, 1):  TurnAction.TURN_LEFT,
    (50, 4, 5):  TurnAction.TURN_RIGHT,

    # ---- Ngã tư 5 (Cross: nối 2, 4, 6, 7) ----
    (2, 5, 4):  TurnAction.TURN_LEFT,
    (2, 5, 6):  TurnAction.TURN_RIGHT,
    (2, 5, 7):  TurnAction.STRAIGHT,
    (4, 5, 2):  TurnAction.TURN_RIGHT,
    (4, 5, 6):  TurnAction.STRAIGHT,
    (4, 5, 7):  TurnAction.TURN_LEFT,
    (6, 5, 2):  TurnAction.TURN_LEFT,
    (6, 5, 4):  TurnAction.STRAIGHT,
    (6, 5, 7):  TurnAction.TURN_RIGHT,
    (7, 5, 2):  TurnAction.STRAIGHT,
    (7, 5, 4):  TurnAction.TURN_RIGHT,
    (7, 5, 6):  TurnAction.TURN_LEFT,

    # ---- Ngã tư 6 (T-junction: nối 3, 5, 51) ----
    (3, 6, 5):   TurnAction.STRAIGHT,
    (3, 6, 51):  TurnAction.TURN_RIGHT,
    (5, 6, 3):   TurnAction.STRAIGHT,
    (5, 6, 51):  TurnAction.TURN_LEFT,
    (51, 6, 3):  TurnAction.TURN_LEFT,
    (51, 6, 5):  TurnAction.TURN_RIGHT,

    # ---- Ngã tư 7 (T-junction: nối 5, 50, 51) ----
    (5, 7, 50):   TurnAction.TURN_LEFT,
    (5, 7, 51):   TurnAction.TURN_RIGHT,

    # ---- Node Đích 50 (Nối 4, 7) – Khi xe đi ngang qua, chưa dừng ----
    (4, 50, 7):   TurnAction.STRAIGHT,
    (7, 50, 4):   TurnAction.STRAIGHT,

    # ---- Node Đích 51 (Nối 6, 7) – Khi xe đi ngang qua, chưa dừng ----
    (6, 51, 7):   TurnAction.STRAIGHT,
    (7, 51, 6):   TurnAction.STRAIGHT,
    (50, 7, 5):   TurnAction.TURN_RIGHT,
    (50, 7, 51):  TurnAction.STRAIGHT,
    (51, 7, 5):   TurnAction.TURN_LEFT,
    (51, 7, 50):  TurnAction.STRAIGHT,
}


def get_action(prev_node: int, curr_node: int, next_node: int) -> TurnAction:
    """Tra bảng hành động tại ngã tư.

    Parameters
    ----------
    prev_node : int
        Node mà xe vừa rời khỏi.
    curr_node : int
        Node (ArUco ID) mà xe vừa nhìn thấy.
    next_node : int
        Node tiếp theo trong lộ trình.

    Returns
    -------
    TurnAction
        Hành động cần thực hiện (STRAIGHT / TURN_LEFT / TURN_RIGHT).

    Raises
    ------
    KeyError
        Nếu bộ ba (prev, curr, next) không tồn tại trong ACTION_MAP.
    """
    key = (prev_node, curr_node, next_node)
    if key not in ACTION_MAP:
        raise KeyError(
            f"Không tìm thấy hành động cho bộ ba ({prev_node}, {curr_node}, {next_node}). "
            f"Kiểm tra lại ACTION_MAP trong map_config.py!"
        )
    return ACTION_MAP[key]
