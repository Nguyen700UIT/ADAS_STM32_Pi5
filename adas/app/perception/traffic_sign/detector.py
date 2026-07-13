from ultralytics import YOLO
import os
class SignDetetor:
    def __int__(self):
        root = os.getcwd()
        path = os.path.join(root, "model/sign_model.onnx")
        self.model = YOLO(path, task="detect")

        self.class_names = self.model.names

    def find_sign(self, frame, conf_thres=0.5, imgsz=320):
        detected_list = []
        results = self.model(frame, conf=conf_thres, imgsz=imgsz, verbose=True)

        for box in results[0].boxes:
            class_id = int(box.cls[0])
            sign_name = self.class_names[class_id]

            if sign_name not in detected_list:
                detected_list.append(sign_name)
        
        return detected_list
    