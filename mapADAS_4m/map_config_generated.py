# Đây là file được tạo tự động bởi tool.
# Tương thích API với app/config/map_config.py.

from enum import Enum


class TurnAction(Enum):
    STRAIGHT = "straight"
    TURN_LEFT = "turn_left"
    TURN_RIGHT = "turn_right"


DIRECTION_NODE_MAX_ID = 49
DESTINATION_NODE_MIN_ID = 50


def is_destination_node(node_id: int) -> bool:
    return node_id >= DESTINATION_NODE_MIN_ID


def is_direction_node(node_id: int) -> bool:
    return 1 <= node_id <= DIRECTION_NODE_MAX_ID

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

ACTION_MAP = {
    (2, 1, 13): 'TURN_LEFT',
    (2, 1, 18): 'FORWARD',
    (13, 1, 2): 'TURN_RIGHT',
    (13, 1, 18): 'TURN_LEFT',
    (18, 1, 2): 'FORWARD',
    (18, 1, 13): 'TURN_RIGHT',
    (1, 2, 4): 'TURN_RIGHT',
    (1, 2, 3): 'TURN_RIGHT',
    (4, 2, 1): 'TURN_LEFT',
    (4, 2, 3): 'TURN_RIGHT',
    (3, 2, 1): 'TURN_LEFT',
    (3, 2, 4): 'TURN_LEFT',
    (2, 3, 4): 'TURN_RIGHT',
    (2, 3, 17): 'TURN_RIGHT',
    (4, 3, 2): 'TURN_LEFT',
    (4, 3, 17): 'TURN_RIGHT',
    (17, 3, 2): 'TURN_LEFT',
    (17, 3, 4): 'TURN_LEFT',
    (2, 4, 3): 'TURN_LEFT',
    (2, 4, 10): 'FORWARD',
    (3, 4, 2): 'TURN_RIGHT',
    (3, 4, 10): 'TURN_LEFT',
    (10, 4, 2): 'FORWARD',
    (10, 4, 3): 'TURN_RIGHT',
    (16, 5, 13): 'TURN_RIGHT',
    (16, 5, 9): 'TURN_LEFT',
    (16, 5, 6): 'FORWARD',
    (13, 5, 16): 'TURN_LEFT',
    (13, 5, 9): 'FORWARD',
    (13, 5, 6): 'TURN_RIGHT',
    (9, 5, 16): 'TURN_RIGHT',
    (9, 5, 13): 'FORWARD',
    (9, 5, 6): 'TURN_LEFT',
    (6, 5, 16): 'FORWARD',
    (6, 5, 13): 'TURN_LEFT',
    (6, 5, 9): 'TURN_RIGHT',
    (14, 6, 15): 'FORWARD',
    (14, 6, 5): 'TURN_LEFT',
    (15, 6, 14): 'FORWARD',
    (15, 6, 5): 'TURN_RIGHT',
    (5, 6, 14): 'TURN_RIGHT',
    (5, 6, 15): 'TURN_LEFT',
    (15, 7, 8): 'TURN_LEFT',
    (15, 7, 9): 'TURN_LEFT',
    (8, 7, 15): 'TURN_RIGHT',
    (8, 7, 9): 'TURN_RIGHT',
    (9, 7, 15): 'TURN_RIGHT',
    (9, 7, 8): 'TURN_LEFT',
    (7, 8, 12): 'TURN_LEFT',
    (12, 8, 7): 'TURN_RIGHT',
    (5, 9, 10): 'TURN_LEFT',
    (5, 9, 7): 'TURN_RIGHT',
    (10, 9, 5): 'TURN_RIGHT',
    (10, 9, 7): 'FORWARD',
    (7, 9, 5): 'TURN_LEFT',
    (7, 9, 10): 'FORWARD',
    (4, 10, 11): 'TURN_LEFT',
    (4, 10, 9): 'TURN_RIGHT',
    (11, 10, 4): 'TURN_RIGHT',
    (11, 10, 9): 'FORWARD',
    (9, 10, 4): 'TURN_LEFT',
    (9, 10, 11): 'FORWARD',
    (17, 11, 10): 'TURN_RIGHT',
    (17, 11, 12): 'TURN_RIGHT',
    (10, 11, 17): 'TURN_LEFT',
    (10, 11, 12): 'TURN_RIGHT',
    (12, 11, 17): 'TURN_LEFT',
    (12, 11, 10): 'TURN_LEFT',
    (8, 12, 11): 'TURN_LEFT',
    (11, 12, 8): 'TURN_RIGHT',
    (52, 13, 1): 'TURN_RIGHT',
    (52, 13, 5): 'TURN_LEFT',
    (1, 13, 52): 'TURN_LEFT',
    (1, 13, 5): 'FORWARD',
    (5, 13, 52): 'TURN_RIGHT',
    (5, 13, 1): 'FORWARD',
    (50, 14, 6): 'TURN_LEFT',
    (50, 14, 18): 'TURN_RIGHT',
    (6, 14, 50): 'TURN_RIGHT',
    (6, 14, 18): 'FORWARD',
    (18, 14, 50): 'TURN_LEFT',
    (18, 14, 6): 'FORWARD',
    (51, 15, 6): 'TURN_RIGHT',
    (51, 15, 7): 'TURN_LEFT',
    (6, 15, 51): 'TURN_LEFT',
    (6, 15, 7): 'FORWARD',
    (7, 15, 51): 'TURN_RIGHT',
    (7, 15, 6): 'FORWARD',
    (53, 16, 5): 'TURN_LEFT',
    (5, 16, 53): 'TURN_RIGHT',
    (3, 17, 54): 'TURN_RIGHT',
    (3, 17, 11): 'FORWARD',
    (54, 17, 3): 'TURN_LEFT',
    (54, 17, 11): 'TURN_RIGHT',
    (11, 17, 3): 'FORWARD',
    (11, 17, 54): 'TURN_LEFT',
    (1, 18, 14): 'TURN_LEFT',
    (14, 18, 1): 'TURN_RIGHT',
}

_ACTION_NAMES = {
    "FORWARD": TurnAction.STRAIGHT,
    "TURN_LEFT": TurnAction.TURN_LEFT,
    "TURN_RIGHT": TurnAction.TURN_RIGHT,
}
ACTION_MAP = {key: _ACTION_NAMES[action] for key, action in ACTION_MAP.items()}


def get_action(prev_node: int, curr_node: int, next_node: int) -> TurnAction:
    key = (prev_node, curr_node, next_node)
    if key not in ACTION_MAP:
        raise KeyError(f"Không tìm thấy hành động cho bộ ba {key}.")
    return ACTION_MAP[key]
