"""
Script Tạo ArUco Marker PDF - Hệ thống ADAS
=============================================
Sinh ra file PDF chứa 23 tấm ArUco Marker chuẩn DICT_4X4_100.
Mỗi tấm được đóng khung vuông kèm nhãn ID để dễ cắt dán lên sa bàn.

Cách chạy:
    python3 generate_aruco_markers.py

Kết quả:
    File PDF "aruco_markers_ADAS.pdf" sẽ được lưu ngay trong thư mục này.
"""

import cv2 as cv
import numpy as np
import os

# ============================================================
# CẤU HÌNH
# ============================================================
DICTIONARY_ID = cv.aruco.DICT_4X4_100  # Chuẩn từ điển ArUco

# Danh sách ID cần in (khớp với map_config.py)
DIRECTION_NODE_IDS = list(range(1, 19))   # Node Hướng (Ngã tư): 1 → 18
DESTINATION_NODE_IDS = [50, 51, 52, 53, 54]  # Node Đích (Bãi đỗ)
ALL_IDS = DIRECTION_NODE_IDS + DESTINATION_NODE_IDS

# Kích thước marker (pixel) - ảnh hưởng đến chất lượng in
MARKER_SIZE_PX = 400  # 400px cho ảnh sắc nét khi in

# Kích thước thực tế khi in (cm)
MARKER_PRINT_SIZE_CM = 5  # 5x5 cm

# Bố cục trên giấy A4 (portrait)
A4_WIDTH_CM = 21.0
A4_HEIGHT_CM = 29.7
COLS_PER_PAGE = 3    # 3 marker mỗi hàng
ROWS_PER_PAGE = 4    # 4 hàng mỗi trang
MARKERS_PER_PAGE = COLS_PER_PAGE * ROWS_PER_PAGE  # 12 marker / trang

# Tên file output
OUTPUT_PDF = "aruco_markers_ADAS.pdf"
OUTPUT_DIR_INDIVIDUAL = "aruco_individual"  # Thư mục chứa ảnh riêng lẻ

# ============================================================
# NHÃN PHÂN LOẠI NODE
# ============================================================
NODE_LABELS = {}
for nid in DIRECTION_NODE_IDS:
    NODE_LABELS[nid] = f"Nga tu {nid}"
NODE_LABELS[50] = "BAI DO 50"
NODE_LABELS[51] = "BAI DO 51"
NODE_LABELS[52] = "BAI DO 52"
NODE_LABELS[53] = "BAI DO 53"
NODE_LABELS[54] = "BAI DO 54"


def generate_single_marker(aruco_dict, marker_id, size_px=400):
    """Sinh ảnh ArUco Marker cho 1 ID."""
    marker_img = cv.aruco.generateImageMarker(aruco_dict, marker_id, size_px)
    return marker_img


def create_framed_marker(aruco_dict, marker_id, size_px=400):
    """Tạo marker có viền trắng + khung đen + nhãn ID bên dưới."""
    marker = generate_single_marker(aruco_dict, marker_id, size_px)

    # Thêm viền trắng xung quanh marker (quan trọng: ArUco cần vùng trắng bao quanh)
    border = int(size_px * 0.15)
    bordered = cv.copyMakeBorder(
        marker, border, border, border, border,
        cv.BORDER_CONSTANT, value=255
    )

    # Thêm vùng nhãn bên dưới
    label_height = int(size_px * 0.25)
    total_h = bordered.shape[0] + label_height
    total_w = bordered.shape[1]

    canvas = np.ones((total_h, total_w), dtype=np.uint8) * 255

    # Đặt marker lên canvas
    canvas[:bordered.shape[0], :bordered.shape[1]] = bordered

    # Vẽ khung đen bao quanh
    cv.rectangle(canvas, (0, 0), (total_w - 1, bordered.shape[0] - 1), 0, 2)

    # Ghi nhãn ID
    label = NODE_LABELS.get(marker_id, f"ID {marker_id}")
    id_text = f"ID: {marker_id}"

    # Dòng 1: ID lớn
    font = cv.FONT_HERSHEY_SIMPLEX
    (tw, th), _ = cv.getTextSize(id_text, font, 1.2, 3)
    tx = (total_w - tw) // 2
    ty = bordered.shape[0] + th + 10
    cv.putText(canvas, id_text, (tx, ty), font, 1.2, 0, 3)

    # Dòng 2: Nhãn mô tả
    (tw2, th2), _ = cv.getTextSize(label, font, 0.6, 2)
    tx2 = (total_w - tw2) // 2
    ty2 = ty + th2 + 12
    cv.putText(canvas, label, (tx2, ty2), font, 0.6, 0, 2)

    return canvas


def save_individual_markers(aruco_dict, ids, output_dir):
    """Lưu từng marker thành file ảnh riêng lẻ."""
    os.makedirs(output_dir, exist_ok=True)

    for mid in ids:
        img = create_framed_marker(aruco_dict, mid, MARKER_SIZE_PX)
        filename = os.path.join(output_dir, f"aruco_id_{mid:02d}.png")
        cv.imwrite(filename, img)

    print(f"[OK] Đã lưu {len(ids)} ảnh marker riêng lẻ vào: {output_dir}/")


def create_pdf_pages(aruco_dict, ids):
    """Tạo các trang A4 chứa nhiều marker, trả về danh sách ảnh trang."""
    # Tính kích thước A4 theo pixel (300 DPI)
    DPI = 300
    a4_w = int(A4_WIDTH_CM / 2.54 * DPI)
    a4_h = int(A4_HEIGHT_CM / 2.54 * DPI)

    # Kích thước 1 ô marker trên giấy
    cell_w = a4_w // COLS_PER_PAGE
    cell_h = a4_h // ROWS_PER_PAGE

    # Kích thước marker thực tế trên giấy (cm → pixel)
    marker_px = int(MARKER_PRINT_SIZE_CM / 2.54 * DPI)

    pages = []
    total_pages = (len(ids) + MARKERS_PER_PAGE - 1) // MARKERS_PER_PAGE

    for page_idx in range(total_pages):
        # Tạo trang trắng A4
        page = np.ones((a4_h, a4_w), dtype=np.uint8) * 255

        start = page_idx * MARKERS_PER_PAGE
        end = min(start + MARKERS_PER_PAGE, len(ids))
        page_ids = ids[start:end]

        for i, mid in enumerate(page_ids):
            row = i // COLS_PER_PAGE
            col = i % COLS_PER_PAGE

            # Tạo marker
            framed = create_framed_marker(aruco_dict, mid, marker_px)

            # Resize nếu cần để vừa ô
            max_dim = min(cell_w, cell_h) - 40  # Margin 20px mỗi bên
            scale = max_dim / max(framed.shape[0], framed.shape[1])
            if scale < 1.0:
                new_w = int(framed.shape[1] * scale)
                new_h = int(framed.shape[0] * scale)
                framed = cv.resize(framed, (new_w, new_h), interpolation=cv.INTER_AREA)

            # Tính vị trí căn giữa trong ô
            x_offset = col * cell_w + (cell_w - framed.shape[1]) // 2
            y_offset = row * cell_h + (cell_h - framed.shape[0]) // 2

            # Đặt marker vào trang
            page[y_offset:y_offset + framed.shape[0],
                 x_offset:x_offset + framed.shape[1]] = framed

        # Vẽ đường cắt (đường kẻ nét đứt nhạt)
        for col in range(1, COLS_PER_PAGE):
            x = col * cell_w
            for y in range(0, a4_h, 20):
                cv.line(page, (x, y), (x, min(y + 10, a4_h)), 200, 1)

        for row in range(1, ROWS_PER_PAGE):
            y = row * cell_h
            for x in range(0, a4_w, 20):
                cv.line(page, (x, y), (min(x + 10, a4_w), y), 200, 1)

        # Thêm tiêu đề trang
        header = f"ADAS ArUco Markers - DICT_4X4_100 - Trang {page_idx + 1}/{total_pages}"
        cv.putText(page, header, (30, 40), cv.FONT_HERSHEY_SIMPLEX, 0.8, 100, 2)

        pages.append(page)

    return pages


def save_pdf(pages, output_path):
    """Lưu các trang thành file PDF."""
    try:
        from PIL import Image
        pil_pages = []
        for page in pages:
            pil_img = Image.fromarray(page)
            pil_pages.append(pil_img)

        if pil_pages:
            pil_pages[0].save(
                output_path,
                save_all=True,
                append_images=pil_pages[1:],
                resolution=300
            )
            print(f"[OK] Đã lưu file PDF: {output_path}")
            return True
    except ImportError:
        print("[WARN] Không tìm thấy thư viện Pillow. Đang cài đặt...")
        os.system("pip install Pillow")
        return save_pdf(pages, output_path)

    return False


def main():
    print("=" * 55)
    print("  SINH ARUCO MARKER CHO HỆ THỐNG ADAS")
    print("=" * 55)
    print(f"  Từ điển: DICT_4X4_100")
    print(f"  Số lượng: {len(ALL_IDS)} marker")
    print(f"  Node Hướng (Ngã tư): {DIRECTION_NODE_IDS}")
    print(f"  Node Đích (Bãi đỗ): {DESTINATION_NODE_IDS}")
    print(f"  Kích thước in: {MARKER_PRINT_SIZE_CM}x{MARKER_PRINT_SIZE_CM} cm")
    print("=" * 55)

    aruco_dict = cv.aruco.getPredefinedDictionary(DICTIONARY_ID)

    # 1. Lưu ảnh riêng lẻ (để in từng tấm nếu cần)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    individual_dir = os.path.join(script_dir, OUTPUT_DIR_INDIVIDUAL)
    save_individual_markers(aruco_dict, ALL_IDS, individual_dir)

    # 2. Tạo PDF gom nhiều marker trên 1 trang A4
    pages = create_pdf_pages(aruco_dict, ALL_IDS)
    pdf_path = os.path.join(script_dir, OUTPUT_PDF)
    saved = save_pdf(pages, pdf_path)

    if saved:
        print()
        print("=" * 55)
        print("  HƯỚNG DẪN IN VÀ DÁN")
        print("=" * 55)
        print(f"  1. Mở file: {OUTPUT_PDF}")
        print(f"  2. In trên giấy A4 (Portrait, 100% scale)")
        print(f"  3. Cắt theo đường nét đứt")
        print(f"  4. Dán lên sa bàn tại vị trí ngã tư/bãi đỗ")
        print(f"     - Dán cách tâm ngã tư 15-20cm")
        print(f"     - Hướng dán: mặt marker ngửa lên trên")
        print("=" * 55)


if __name__ == "__main__":
    main()
