import cv2, time

class Video:
    def __init__(self, cfg):
        vcfg = cfg["video"]
        self.cap = cv2.VideoCapture(vcfg.get("camera_index", 0), cv2.CAP_DSHOW if hasattr(cv2, "CAP_DSHOW") else 0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, vcfg.get("width", 1280))
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, vcfg.get("height", 720))
        self.cap.set(cv2.CAP_PROP_FPS, vcfg.get("fps_min", 60))
        self.roi = vcfg["roi"]  # [x,y,w,h] in normalized coords

    def read(self):
        ok, frame = self.cap.read()
        if not ok: return None
        return frame

    def release(self):
        if self.cap: self.cap.release()
