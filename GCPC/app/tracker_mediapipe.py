# -*- coding: utf-8 -*-


def _clamp01(value: float) -> float:
    """Clamp numeric value to normalized [0..1] range."""
    return max(0.0, min(1.0, value))


class MediaPipeHandTracker:
    """Wrapper around MediaPipe Hands providing a common tracker interface."""

    def __init__(self, min_det=0.6, min_trk=0.5, max_hands=2, model_complexity=1):
        import mediapipe as mp

        self.mp = mp
        self.providers = ["mediapipe"]
        self.hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=max_hands,
            model_complexity=model_complexity,
            min_detection_confidence=min_det,
            min_tracking_confidence=min_trk,
        )

    def process(self, rgb):
        """Run MediaPipe on an RGB frame and return normalized landmarks."""
        results = self.hands.process(rgb)
        if not results.multi_hand_landmarks:
            return []

        out = []
        for lm, handed in zip(results.multi_hand_landmarks, results.multi_handedness):
            pts = [(_clamp01(float(p.x)), _clamp01(float(p.y))) for p in lm.landmark]
            if handed and handed.classification:
                score = float(handed.classification[0].score)
                label = handed.classification[0].label
            else:
                score = 0.0
                label = "Unknown"
            out.append({"lm": pts, "label": label, "score": score})
        return out
