import numpy as np
from dataclasses import dataclass
from typing import Optional, List, Tuple

# MediaPipe Tasks imports
try:
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision
    from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions, HandLandmarkerResult, RunningMode
    MP_OK = True
except Exception as e:
    MP_OK = False
    HandLandmarker = None
    HandLandmarkerOptions = None
    HandLandmarkerResult = None
    RunningMode = None

@dataclass
class HandResult:
    handedness: str
    landmarks: np.ndarray  # (21,3) normalized
    world_landmarks: Optional[np.ndarray] = None
    score: float = 0.0

class HandTracker:
    def __init__(self, cfg):
        if not MP_OK:
            raise RuntimeError("MediaPipe not available. Install mediapipe>=0.10.")
        model_path = cfg["models"]["hand_landmarker"]
        base_opts = mp_python.BaseOptions(model_asset_path=model_path)
        opts = HandLandmarkerOptions(
            base_options=base_opts,
            num_hands=1,
            running_mode=RunningMode.VIDEO,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.task = HandLandmarker.create_from_options(opts)

    def process(self, frame_bgr, timestamp_ms: int) -> Optional[HandResult]:
        h, w = frame_bgr.shape[:2]
        # MediaPipe expects RGB
        frame_rgb = frame_bgr[:, :, ::-1]
        mp_image = mp_vision.Image(image_format=mp_vision.ImageFormat.SRGB, data=frame_rgb)
        res: HandLandmarkerResult = self.task.detect_for_video(mp_image, timestamp_ms)
        if not res or len(res.handedness) == 0 or len(res.hand_landmarks) == 0:
            return None
        # Choose best hand (highest score)
        idx = 0
        handedness = res.handedness[idx][0].category_name
        score = res.handedness[idx][0].score
        pts = np.array([[lm.x, lm.y, lm.z] for lm in res.hand_landmarks[idx]], dtype=np.float32)
        return HandResult(handedness=handedness, landmarks=pts, world_landmarks=None, score=score)
