import cv2 as cv 

class Webcam:
    def __init__(self):
        self.cap = cv.VideoCapture(0)
    
    def read(self):
        return self.cap.read()
    
    def release(self):
        self.cap.release()
    