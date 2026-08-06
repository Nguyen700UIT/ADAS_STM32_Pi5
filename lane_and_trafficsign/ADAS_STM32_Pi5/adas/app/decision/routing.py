# =============================================================================
# Routing Engine – Thuật toán State-based Dijkstra chặn U-Turn
# =============================================================================
# Module này chứa thuật toán tìm đường đi ngắn nhất (Shortest Path)
# sử dụng biến thể Dijkstra theo Trạng thái (State-based Dijkstra).
#
# Khác biệt với Dijkstra chuẩn:
#   - State = (prev_node, curr_node) thay vì chỉ curr_node.
#   - Nếu next_node == prev_node → trọng số = ∞ (cấm quay đầu).
#
# Kết quả: Trả về danh sách Node theo thứ tự đi (path) và tổng khoảng cách.
# =============================================================================

import heapq

import sys
from pathlib import Path

_FILE_DIR = Path(__file__).resolve().parent
_APP_DIR = _FILE_DIR.parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

try:
    from ..config import map_config
except ImportError:
    from config import map_config


# Giá trị "vô cực" dùng để chặn cạnh quay đầu
INF = float('inf')


class RoutingEngine:
    """Thuật toán tìm đường State-based Dijkstra chặn U-Turn.

    Attributes
    ----------
    graph : dict
        Đồ thị từ ``map_config.GRAPH``.

    Usage
    -----
    >>> router = RoutingEngine()
    >>> path, cost = router.find_path(start=1, goal=51)
    >>> print(f"Lộ trình: {path}, Chi phí: {cost}cm")
    """

    def __init__(self, graph=None):
        """Khởi tạo Routing Engine.

        Parameters
        ----------
        graph : dict, optional
            Đồ thị tùy chỉnh. Nếu ``None``, sử dụng ``map_config.GRAPH``.
        """
        self.graph = graph if graph is not None else map_config.GRAPH

    def find_path(self, start, goal, initial_prev=None):
        """Tìm đường đi ngắn nhất từ ``start`` đến ``goal``, chặn quay đầu.

        Thuật toán Dijkstra theo trạng thái (State-based Dijkstra):
        - State = (prev_node, curr_node)
        - Khi mở rộng sang next_node:
          + Nếu next_node == prev_node → trọng số = ∞ (cấm quay đầu)
          + Ngược lại → trọng số bình thường từ GRAPH

        Parameters
        ----------
        start : int
            ID của Node xuất phát (ArUco ID).
        goal : int
            ID của Node đích đến (ArUco ID).
        initial_prev : int or None, optional
            ID của Node trước ``start`` (nếu xe đang di chuyển giữa chừng).
            Nếu ``None``, xe chưa đi qua node nào (khởi đầu).

        Returns
        -------
        tuple[list[int], float]
            - ``path``: Danh sách ID node theo thứ tự đi [start, ..., goal].
                        Trả về danh sách rỗng ``[]`` nếu không tìm được đường.
            - ``cost``: Tổng khoảng cách (cm). Trả về ``INF`` nếu không có đường.

        Examples
        --------
        >>> router = RoutingEngine()
        >>> path, cost = router.find_path(1, 51)
        >>> print(path)   # [1, 2, 5, 6, 51]  (ví dụ)
        >>> print(cost)   # 120.0              (ví dụ)
        """
        if start not in self.graph:
            return [], INF
        if goal not in self.graph:
            return [], INF
        if start == goal:
            return [start], 0

        # State: (prev_node, curr_node)
        # prev_node = None nghĩa là xe vừa khởi đầu, chưa đi qua node nào
        start_state = (initial_prev, start)

        # Priority queue: (cost, state)
        pq = [(0, start_state)]

        # Best known cost cho mỗi state
        dist = {start_state: 0}

        # Truy vết đường đi: state -> state trước đó
        parent = {start_state: None}

        while pq:
            current_cost, (prev, curr) = heapq.heappop(pq)

            # Đã đến đích!
            if curr == goal:
                return self._reconstruct_path(parent, (prev, curr)), current_cost

            # Skip nếu đã tìm được đường ngắn hơn đến state này
            if current_cost > dist.get((prev, curr), INF):
                continue

            # Duyệt tất cả node kề
            for next_node, weight in self.graph.get(curr, {}).items():
                # ==========================================
                # CHẶN QUAY ĐẦU: next_node == prev → INF
                # ==========================================
                if next_node == prev:
                    edge_cost = INF
                else:
                    edge_cost = weight

                new_cost = current_cost + edge_cost
                next_state = (curr, next_node)

                # Chỉ cập nhật nếu tìm được đường ngắn hơn
                if new_cost < dist.get(next_state, INF):
                    dist[next_state] = new_cost
                    parent[next_state] = (prev, curr)
                    heapq.heappush(pq, (new_cost, next_state))

        # Không tìm được đường đi
        return [], INF

    def _reconstruct_path(self, parent, goal_state):
        """Truy vết ngược từ goal_state về start_state để lấy đường đi.

        Parameters
        ----------
        parent : dict
            Bảng truy vết (state -> state trước đó).
        goal_state : tuple
            State đích (prev_node, goal_node).

        Returns
        -------
        list[int]
            Danh sách node theo thứ tự đi.
        """
        path = []
        state = goal_state
        while state is not None:
            _, curr = state
            path.append(curr)
            state = parent.get(state)
        path.reverse()

        # Loại bỏ node trùng lặp đầu tiên (nếu có)
        if len(path) > 1 and path[0] == path[1]:
            path = path[1:]

        return path

    def get_next_action(self, prev_node, curr_node, next_node):
        """Tra bảng Action Map để lấy hành động rẽ tại ngã tư hiện tại.

        Parameters
        ----------
        prev_node : int
            Node vừa rời khỏi.
        curr_node : int
            Node hiện tại (ArUco ID vừa nhìn thấy).
        next_node : int
            Node tiếp theo trong lộ trình.

        Returns
        -------
        TurnAction
            Hành động cần thực hiện.
        """
        return map_config.get_action(prev_node, curr_node, next_node)


# =============================================================================
# CLI Test – Chạy trực tiếp file này trên Terminal để test thuật toán
# =============================================================================
# Cách chạy:
#   cd lane_and_trafficsign/ADAS_STM32_Pi5/adas/app
#   python -m decision.routing
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  TEST: State-based Dijkstra (Chặn U-Turn)")
    print("=" * 60)

    router = RoutingEngine()

    # Liệt kê tất cả Node trong đồ thị
    all_nodes = sorted(router.graph.keys())
    print(f"\n📍 Các Node trong đồ thị: {all_nodes}")
    print(f"   Node Hướng (Ngã tư):  {[n for n in all_nodes if map_config.is_direction_node(n)]}")
    print(f"   Node Đích (Bãi đỗ):   {[n for n in all_nodes if map_config.is_destination_node(n)]}")

    # Test Case 1: Tìm đường từ Node 1 đến Node 51
    print("\n" + "-" * 60)
    print("📋 Test Case 1: Node 1 → Node 51")
    path, cost = router.find_path(start=1, goal=51)
    print(f"   Lộ trình: {' → '.join(map(str, path))}")
    print(f"   Tổng khoảng cách: {cost} cm")

    # In hành động tại mỗi ngã tư
    if len(path) >= 3:
        print("   Hành động tại mỗi ngã tư:")
        for i in range(1, len(path) - 1):
            prev, curr, nxt = path[i - 1], path[i], path[i + 1]
            try:
                action = router.get_next_action(prev, curr, nxt)
                print(f"     Tại Node {curr}: đi từ {prev}, sang {nxt} → {action.value}")
            except KeyError as e:
                print(f"     ⚠️ {e}")

    # Test Case 2: Tìm đường từ Node 50 đến Node 3
    print("\n" + "-" * 60)
    print("📋 Test Case 2: Node 50 → Node 3")
    path2, cost2 = router.find_path(start=50, goal=3)
    print(f"   Lộ trình: {' → '.join(map(str, path2))}")
    print(f"   Tổng khoảng cách: {cost2} cm")

    if len(path2) >= 3:
        print("   Hành động tại mỗi ngã tư:")
        for i in range(1, len(path2) - 1):
            prev, curr, nxt = path2[i - 1], path2[i], path2[i + 1]
            try:
                action = router.get_next_action(prev, curr, nxt)
                print(f"     Tại Node {curr}: đi từ {prev}, sang {nxt} → {action.value}")
            except KeyError as e:
                print(f"     ⚠️ {e}")

    # Test Case 3: Kiểm tra chặn quay đầu
    print("\n" + "-" * 60)
    print("📋 Test Case 3: Chặn Quay Đầu - Node 1 → Node 2 (prev=2)")
    path3, cost3 = router.find_path(start=1, goal=2, initial_prev=2)
    if cost3 == INF:
        print("   ✅ Thuật toán đã CHẶN thành công quay đầu! (Cost = ∞)")
    else:
        print(f"   Lộ trình vòng: {' → '.join(map(str, path3))}")
        print(f"   Tổng khoảng cách: {cost3} cm")
        print("   ✅ Thuật toán tìm đường VÒNG thay vì quay đầu!")

    print("\n" + "=" * 60)
    print("  TEST HOÀN TẤT")
    print("=" * 60)
