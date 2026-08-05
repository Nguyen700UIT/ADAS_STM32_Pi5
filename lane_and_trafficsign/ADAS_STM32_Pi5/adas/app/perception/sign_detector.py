from ultralytics import YOLO
import os
from pathlib import Path

class SignDetector:
    def __init__(self):
        # Tìm model theo thứ tự ưu tiên:
        # 1. model/sign_model.onnx (relative to project root)
        # 2. yolov8n.pt ở project root (fallback)
        # 3. Tự tải yolov8n.pt từ mạng (fallback cuối cùng)
        
        _file_dir = Path(__file__).resolve().parent
        # Từ perception/traffic_sign/ → lên 5 cấp → ADAS_STM32_Pi5 (workspace root)
        _workspace_root = _file_dir.parents[5]
        
        # Thử tìm model chuyên dụng biển báo
        model_candidates = [
            _workspace_root / "model" / "sign_model.onnx",
            _file_dir / "model" / "sign_model.onnx",
            _workspace_root / "yolov8n.pt",
        ]
        
        loaded = False
        for path in model_candidates:
            if path.exists():
                self.model = YOLO(str(path), task="detect")
                print(f"[INFO] Đã nạp AI nhận diện biển báo từ: {path}")
                loaded = True
                break
        
        if not loaded:
            print("[WARNING] Không tìm thấy file model biển báo!")
            print("[WARNING] Sẽ tự động tải model YOLOv8 mặc định (yolov8n.pt) để test luồng chạy...")
            self.model = YOLO("yolov8n.pt")  # Tự động tải từ mạng về nếu chưa có
            
        self.class_names = self.model.names

    def find_sign(self, frame, conf_thres=0.5, imgsz=320):
        detected_list = []
        results = self.model(frame, conf=conf_thres, imgsz=imgsz, verbose=False)

        for box in results[0].boxes:
            class_id = int(box.cls[0])
            sign_name = self.class_names[class_id]

            if sign_name not in detected_list:
                detected_list.append(sign_name)
        
        return detected_list