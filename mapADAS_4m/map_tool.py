import cv2
import numpy as np
import math
import json
import os

# Cấu hình
IMAGE_PATH = '1785771903086-e9202f51-5f19-4a38-9a7c-3fa573d613de_1.jpg'
CM_PER_PIXEL = 0.4 # Tỉ lệ quy đổi từ pixel ra centimet (có thể tinh chỉnh lại)

nodes = {} # Lưu trữ ID và tọa độ: {id: (x, y)}
edges = [] # Lưu trữ các cạnh nối: [(id1, id2), ...]
next_intersection_id = 1
next_endpoint_id = 50
selected_node = None

def calculate_angle(p1, p2, p3):
    """Tính góc giữa 2 vector p1->p2 và p2->p3 để xác định hướng rẽ"""
    v1 = (p2[0] - p1[0], p2[1] - p1[1])
    v2 = (p3[0] - p2[0], p3[1] - p2[1])
    
    dot_product = v1[0]*v2[0] + v1[1]*v2[1]
    cross_product = v1[0]*v2[1] - v1[1]*v2[0]
    
    # Tính góc theo độ (-180 đến 180)
    angle = math.degrees(math.atan2(cross_product, dot_product))
    return angle

def get_action(angle):
    """Xác định hành động rẽ dựa vào góc lệch"""
    if abs(angle) < 30:
        return "FORWARD"
    elif angle > 0:
        return "TURN_RIGHT"
    else:
        return "TURN_LEFT"


ACTION_TO_ENUM = {
    "FORWARD": "STRAIGHT",
    "TURN_LEFT": "TURN_LEFT",
    "TURN_RIGHT": "TURN_RIGHT",
}

def mouse_callback(event, x, y, flags, param):
    global next_intersection_id, next_endpoint_id, selected_node, nodes, edges
    
    # 1. TẠO NODE MỚI (CLICK ĐÚP CHUỘT TRÁI)
    if event == cv2.EVENT_LBUTTONDBLCLK:
        # Tránh việc click trùng vào node đã có
        for nid, pos in nodes.items():
            if math.hypot(pos[0]-x, pos[1]-y) < 15:
                return 
        
        # Phân biệt Ngã tư và Điểm đỗ (Nhấn giữ Shift + Double click để tạo điểm đỗ)
        if flags & cv2.EVENT_FLAG_SHIFTKEY:
            nid = next_endpoint_id
            next_endpoint_id += 1
        else:
            nid = next_intersection_id
            next_intersection_id += 1
            
        nodes[nid] = (x, y)
        print(f"[+] Đã thêm Node {nid} tại ({x}, {y})")
        
    # 2. CHỌN NODE HOẶC NỐI ĐƯỜNG (CLICK CHUỘT TRÁI 1 LẦN)
    elif event == cv2.EVENT_LBUTTONDOWN:
        for nid, pos in nodes.items():
            if math.hypot(pos[0]-x, pos[1]-y) < 15:
                if selected_node is None:
                    selected_node = nid
                    print(f"[*] Đã chọn Node {nid}")
                else:
                    if selected_node != nid:
                        # Nối thành 1 cạnh (edge)
                        edge = (min(selected_node, nid), max(selected_node, nid))
                        if edge not in edges:
                            edges.append(edge)
                            print(f"[+] Đã NỐI đường giữa Node {selected_node} và Node {nid}")
                        else:
                            edges.remove(edge) # Nếu đã nối rồi thì xóa đi (Toggle)
                            print(f"[-] Đã XÓA đường nối giữa Node {selected_node} và Node {nid}")
                    selected_node = None # Hủy chọn sau khi thao tác
                return
        selected_node = None # Click ra chỗ trống thì hủy chọn

    # 3. XÓA NODE VÀ CÁC ĐƯỜNG LIÊN QUAN (CLICK CHUỘT PHẢI)
    elif event == cv2.EVENT_RBUTTONDOWN:
        for nid, pos in list(nodes.items()):
            if math.hypot(pos[0]-x, pos[1]-y) < 15:
                del nodes[nid] # Xóa node
                # Xóa luôn các đường có chứa node này
                edges = [e for e in edges if e[0] != nid and e[1] != nid]
                print(f"[-] Đã XÓA TẬN GỐC Node {nid} và các đường đi qua nó")
                if selected_node == nid:
                    selected_node = None
                return

def export_config():
    """Xuất ra định dạng python dict cho file map_config.py"""
    if not nodes:
        print("[-] Không có Node nào để xuất!")
        return

    graph = {n: {} for n in nodes}
    
    # 1. Tính toán GRAPH (Đo khoảng cách)
    for e in edges:
        n1, n2 = e
        p1, p2 = nodes[n1], nodes[n2]
        dist_px = math.hypot(p1[0]-p2[0], p1[1]-p2[1])
        dist_cm = round(dist_px * CM_PER_PIXEL)
        graph[n1][n2] = dist_cm
        graph[n2][n1] = dist_cm
        
    action_map = {}
    
    # 2. Tính toán ACTION_MAP (Góc rẽ cho tất cả tổ hợp Prev -> Curr -> Next)
    for b in nodes: # b là điểm Curr hiện tại
        neighbors = list(graph[b].keys())
        for a in neighbors: # a là điểm Prev
            for c in neighbors: # c là điểm Next
                if a != c:
                    angle = calculate_angle(nodes[a], nodes[b], nodes[c])
                    action = get_action(angle)
                    action_map[(a, b, c)] = action
                    
    # 3. Ghi ra file
    output_str = "# Đây là file được tạo tự động bởi map_tool.py\n"
    output_str += "# Có thể copy trực tiếp vào app/config/map_config.py.\n\n"
    output_str += "from enum import Enum\n\n"
    output_str += "class TurnAction(Enum):\n"
    output_str += "    STRAIGHT = 'straight'\n"
    output_str += "    TURN_LEFT = 'turn_left'\n"
    output_str += "    TURN_RIGHT = 'turn_right'\n\n"
    output_str += "DIRECTION_NODE_MAX_ID = 49\n"
    output_str += "DESTINATION_NODE_MIN_ID = 50\n\n"
    output_str += "def is_destination_node(node_id: int) -> bool:\n"
    output_str += "    return node_id >= DESTINATION_NODE_MIN_ID\n\n"
    output_str += "def is_direction_node(node_id: int) -> bool:\n"
    output_str += "    return 1 <= node_id <= DIRECTION_NODE_MAX_ID\n\n"
    
    output_str += "GRAPH = {\n"
    for k, v in graph.items():
        output_str += f"    {k}: {v},\n"
    output_str += "}\n\n"
    
    output_str += "ACTION_MAP = {\n"
    for key, action in action_map.items():
        output_str += f"    {key}: TurnAction.{ACTION_TO_ENUM[action]},\n"
    output_str += "}\n\n"
    output_str += "def get_action(prev_node: int, curr_node: int, next_node: int) -> TurnAction:\n"
    output_str += "    key = (prev_node, curr_node, next_node)\n"
    output_str += "    if key not in ACTION_MAP:\n"
    output_str += "        raise KeyError(f'Không tìm thấy hành động cho bộ ba {key}.')\n"
    output_str += "    return ACTION_MAP[key]\n"
    
    with open('map_config_generated.py', 'w', encoding='utf-8') as f:
        f.write(output_str)
    print("\n[OK] Đã xuất thành công ra file: map_config_generated.py !")

def main():
    if not os.path.exists(IMAGE_PATH):
        print(f"Lỗi: Không tìm thấy ảnh tại đường dẫn {IMAGE_PATH}")
        return
        
    img = cv2.imread(IMAGE_PATH)
    cv2.namedWindow('Map Annotator Tool', cv2.WINDOW_NORMAL)
    cv2.setMouseCallback('Map Annotator Tool', mouse_callback)
    
    print("=============================================")
    print("🎯 CÔNG CỤ TẠO GRAPH & ACTION_MAP (OpenCV)")
    print("=============================================")
    print("1. [Click đúp chuột TRÁI]       : Tạo NGÃ TƯ (ID từ 1-49)")
    print("2. [Giữ SHIFT + Đúp chuột TRÁI] : Tạo ĐIỂM ĐỖ (ID từ 50-99)")
    print("3. [Click Node A -> Node B]     : NỐI / XÓA NỐI 2 điểm")
    print("4. [Click chuột PHẢI vào Node]  : XÓA Node")
    print("5. Nhấn phím 'e'                : Xuất ra file config")
    print("6. Nhấn phím 'q' hoặc ESC       : Thoát")
    print("=============================================")
    
    global selected_node
    while True:
        display = img.copy()
        
        # Vẽ các con đường
        for e in edges:
            p1 = nodes[e[0]]
            p2 = nodes[e[1]]
            cv2.line(display, p1, p2, (0, 255, 255), 2)
            
        # Vẽ các Node
        for nid, pos in nodes.items():
            color = (0, 255, 0) if nid < 50 else (0, 0, 255) # Ngã tư màu xanh lá, điểm đỗ màu đỏ
            if selected_node == nid:
                cv2.circle(display, pos, 8, (255, 0, 0), -1) # Chuyển màu xanh lam nếu đang được chọn
            else:
                cv2.circle(display, pos, 6, color, -1)
            cv2.putText(display, str(nid), (pos[0]+10, pos[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
        cv2.imshow('Map Annotator Tool', display)
        key = cv2.waitKey(20) & 0xFF
        
        if key == 27 or key == ord('q'):
            break
        elif key == ord('e'):
            export_config()
            
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
