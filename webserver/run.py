import sys
import os
import argparse

# Lấy đường dẫn thư mục gốc của project (ADAS_STM32_Pi5)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def main():
    parser = argparse.ArgumentParser(description="Khởi chạy Webserver cho ADAS")
    parser.add_argument('--mode', type=str, choices=['lane', 'sign'], default='lane',
                        help="Chọn phiên bản AI để chạy webserver cùng (lane: bám làn, sign: biển báo). Mặc định: lane")
    args = parser.parse_args()

    if args.mode == 'lane':
        adas_path = os.path.join(ROOT_DIR, "lane_control", "ADAS_STM32_Pi5", "adas")
    else:
        adas_path = os.path.join(ROOT_DIR, "traffic_sign_detection", "ADAS_STM32_Pi5", "adas")

    if not os.path.exists(adas_path):
        print(f"Lỗi: Không tìm thấy thư mục {adas_path}")
        sys.exit(1)

    # Thêm đường dẫn vào sys.path để các file trong server có thể import 'app'
    sys.path.insert(0, adas_path)
    
    print(f"[*] Đang khởi động Webserver với phiên bản: {args.mode.upper()}...")
    print(f"[*] Đường dẫn AI module (app): {adas_path}")

    # Đảm bảo import stream, state từ thư mục webserver hiện tại
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    # Chạy Flask server từ server.py
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    import server
    server.app.run(host="0.0.0.0", port=5000)

if __name__ == "__main__":
    main()
