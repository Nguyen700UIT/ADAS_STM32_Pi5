# =============================================================================
# Map Configuration – Bản đồ số của sa hình ADAS
# =============================================================================
# File này chứa toàn bộ thông tin Đồ thị (Graph) đã được "phiên dịch"
# từ ảnh chụp sa hình (mapADAS_4m) sang cấu trúc dữ liệu Python.
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
GRAPH = {
    1: {2: 112, 13: 109, 18: 67},
    2: {1: 112, 4: 142, 3: 154},
    3: {2: 154, 4: 113, 17: 77},
    4: {2: 142, 3: 113, 10: 117},
    5: {16: 81, 13: 69, 9: 84, 6: 118},
    6: {14: 56, 15: 60, 5: 118},
    7: {15: 27, 8: 121, 9: 119},
    8: {7: 121, 12: 180},
    9: {5: 84, 10: 120, 7: 119},
    10: {4: 117, 11: 108, 9: 120},
    11: {17: 84, 10: 108, 12: 113},
    12: {8: 180, 11: 113},
    50: {14: 42},
    51: {15: 40},
    52: {13: 36},
    53: {16: 31},
    54: {17: 52},
    13: {52: 36, 1: 109, 5: 69},
    14: {50: 42, 6: 56, 18: 130},
    15: {51: 40, 6: 60, 7: 27},
    16: {53: 31, 5: 81},
    17: {3: 77, 54: 52, 11: 84},
    18: {1: 67, 14: 130},
}


# =============================================================================
# BẢNG HÀNH ĐỘNG – Action Map
# =============================================================================
ACTION_MAP = {
    (2, 1, 13): TurnAction.TURN_LEFT,
    (2, 1, 18): TurnAction.STRAIGHT,
    (13, 1, 2): TurnAction.TURN_RIGHT,
    (13, 1, 18): TurnAction.TURN_LEFT,
    (18, 1, 2): TurnAction.STRAIGHT,
    (18, 1, 13): TurnAction.TURN_RIGHT,
    (1, 2, 4): TurnAction.TURN_RIGHT,
    (1, 2, 3): TurnAction.TURN_RIGHT,
    (4, 2, 1): TurnAction.TURN_LEFT,
    (4, 2, 3): TurnAction.TURN_RIGHT,
    (3, 2, 1): TurnAction.TURN_LEFT,
    (3, 2, 4): TurnAction.TURN_LEFT,
    (2, 3, 4): TurnAction.TURN_RIGHT,
    (2, 3, 17): TurnAction.TURN_RIGHT,
    (4, 3, 2): TurnAction.TURN_LEFT,
    (4, 3, 17): TurnAction.TURN_RIGHT,
    (17, 3, 2): TurnAction.TURN_LEFT,
    (17, 3, 4): TurnAction.TURN_LEFT,
    (2, 4, 3): TurnAction.TURN_LEFT,
    (2, 4, 10): TurnAction.STRAIGHT,
    (3, 4, 2): TurnAction.TURN_RIGHT,
    (3, 4, 10): TurnAction.TURN_LEFT,
    (10, 4, 2): TurnAction.STRAIGHT,
    (10, 4, 3): TurnAction.TURN_RIGHT,
    (16, 5, 13): TurnAction.TURN_RIGHT,
    (16, 5, 9): TurnAction.TURN_LEFT,
    (16, 5, 6): TurnAction.STRAIGHT,
    (13, 5, 16): TurnAction.TURN_LEFT,
    (13, 5, 9): TurnAction.STRAIGHT,
    (13, 5, 6): TurnAction.TURN_RIGHT,
    (9, 5, 16): TurnAction.TURN_RIGHT,
    (9, 5, 13): TurnAction.STRAIGHT,
    (9, 5, 6): TurnAction.TURN_LEFT,
    (6, 5, 16): TurnAction.STRAIGHT,
    (6, 5, 13): TurnAction.TURN_LEFT,
    (6, 5, 9): TurnAction.TURN_RIGHT,
    (14, 6, 15): TurnAction.STRAIGHT,
    (14, 6, 5): TurnAction.TURN_LEFT,
    (15, 6, 14): TurnAction.STRAIGHT,
    (15, 6, 5): TurnAction.TURN_RIGHT,
    (5, 6, 14): TurnAction.TURN_RIGHT,
    (5, 6, 15): TurnAction.TURN_LEFT,
    (15, 7, 8): TurnAction.TURN_LEFT,
    (15, 7, 9): TurnAction.TURN_LEFT,
    (8, 7, 15): TurnAction.TURN_RIGHT,
    (8, 7, 9): TurnAction.TURN_RIGHT,
    (9, 7, 15): TurnAction.TURN_RIGHT,
    (9, 7, 8): TurnAction.TURN_LEFT,
    (7, 8, 12): TurnAction.TURN_LEFT,
    (12, 8, 7): TurnAction.TURN_RIGHT,
    (5, 9, 10): TurnAction.TURN_LEFT,
    (5, 9, 7): TurnAction.TURN_RIGHT,
    (10, 9, 5): TurnAction.TURN_RIGHT,
    (10, 9, 7): TurnAction.STRAIGHT,
    (7, 9, 5): TurnAction.TURN_LEFT,
    (7, 9, 10): TurnAction.STRAIGHT,
    (4, 10, 11): TurnAction.TURN_LEFT,
    (4, 10, 9): TurnAction.TURN_RIGHT,
    (11, 10, 4): TurnAction.TURN_RIGHT,
    (11, 10, 9): TurnAction.STRAIGHT,
    (9, 10, 4): TurnAction.TURN_LEFT,
    (9, 10, 11): TurnAction.STRAIGHT,
    (17, 11, 10): TurnAction.TURN_RIGHT,
    (17, 11, 12): TurnAction.TURN_RIGHT,
    (10, 11, 17): TurnAction.TURN_LEFT,
    (10, 11, 12): TurnAction.TURN_RIGHT,
    (12, 11, 17): TurnAction.TURN_LEFT,
    (12, 11, 10): TurnAction.TURN_LEFT,
    (8, 12, 11): TurnAction.TURN_LEFT,
    (11, 12, 8): TurnAction.TURN_RIGHT,
    (52, 13, 1): TurnAction.TURN_RIGHT,
    (52, 13, 5): TurnAction.TURN_LEFT,
    (1, 13, 52): TurnAction.TURN_LEFT,
    (1, 13, 5): TurnAction.STRAIGHT,
    (5, 13, 52): TurnAction.TURN_RIGHT,
    (5, 13, 1): TurnAction.STRAIGHT,
    (50, 14, 6): TurnAction.TURN_LEFT,
    (50, 14, 18): TurnAction.TURN_RIGHT,
    (6, 14, 50): TurnAction.TURN_RIGHT,
    (6, 14, 18): TurnAction.STRAIGHT,
    (18, 14, 50): TurnAction.TURN_LEFT,
    (18, 14, 6): TurnAction.STRAIGHT,
    (51, 15, 6): TurnAction.TURN_RIGHT,
    (51, 15, 7): TurnAction.TURN_LEFT,
    (6, 15, 51): TurnAction.TURN_LEFT,
    (6, 15, 7): TurnAction.STRAIGHT,
    (7, 15, 51): TurnAction.TURN_RIGHT,
    (7, 15, 6): TurnAction.STRAIGHT,
    (53, 16, 5): TurnAction.TURN_LEFT,
    (5, 16, 53): TurnAction.TURN_RIGHT,
    (3, 17, 54): TurnAction.TURN_RIGHT,
    (3, 17, 11): TurnAction.STRAIGHT,
    (54, 17, 3): TurnAction.TURN_LEFT,
    (54, 17, 11): TurnAction.TURN_RIGHT,
    (11, 17, 3): TurnAction.STRAIGHT,
    (11, 17, 54): TurnAction.TURN_LEFT,
    (1, 18, 14): TurnAction.TURN_LEFT,
    (14, 18, 1): TurnAction.TURN_RIGHT,
}

def get_action(prev_node: int, curr_node: int, next_node: int) -> TurnAction:
    """Tra bảng hành động tại ngã tư."""
    key = (prev_node, curr_node, next_node)
    if key not in ACTION_MAP:
        raise KeyError(
            f"Không tìm thấy hành động cho bộ ba ({prev_node}, {curr_node}, {next_node}). "
        )
    return ACTION_MAP[key]
