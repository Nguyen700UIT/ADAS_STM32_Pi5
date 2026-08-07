import sys
import os
import argparse

# Lấy đường dẫn thư mục gốc của project (ADAS_STM32_Pi5)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def main():
    parser = argparse.ArgumentParser(description="Khởi chạy Webserver cho ADAS")
    args = parser.parse_args()

    adas_path = os.path.join(ROOT_DIR, "lane_and_trafficsign", "ADAS_STM32_Pi5", "adas")

    if not os.path.exists(adas_path):
        print(f"Lỗi: Không tìm thấy thư mục {adas_path}")
        sys.exit(1)

    # Thêm đường dẫn vào sys.path để các file trong server có thể import 'app'
    sys.path.insert(0, adas_path)
    
    print(f"[*] Đang khởi động Webserver...")
    print(f"[*] Đường dẫn AI module (app): {adas_path}")

    # Đảm bảo import stream, state từ thư mục root (đã add ở trên)
    sys.path.insert(0, ROOT_DIR)

    # Chạy Flask server từ server.py
    os.chdir(ROOT_DIR)
    from webserver import server
    server.app.run(host="0.0.0.0", port=5000)

if __name__ == "__main__":
    main()
