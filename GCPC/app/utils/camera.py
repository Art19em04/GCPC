"""Camera and drawing helpers."""

import cv2


_BACKENDS = tuple(
    dict.fromkeys(
        api
        for api in (
            getattr(cv2, "CAP_MSMF", None),
            getattr(cv2, "CAP_DSHOW", None),
            getattr(cv2, "CAP_ANY", None),
        )
        if api is not None
    )
)
_PROBE_RANGE = range(0, 6)


def _open_with_backend(index: int, api: int, width: int, height: int):
    """Open camera index with a specific backend and verify first frame read."""
    cap = cv2.VideoCapture(index, api)
    if not cap or not cap.isOpened():
        if cap:
            cap.release()
        return None
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    ok, _ = cap.read()
    if not ok:
        cap.release()
        return None
    return cap


def open_camera(idx: int, w: int, h: int):
    """Try to open camera by preferred index with fallbacks across APIs."""
    indices = (-1, *_PROBE_RANGE) if idx == -1 else (idx,)
    for cam_idx in indices:
        for api in _BACKENDS:
            cap = _open_with_backend(cam_idx, api, w, h)
            if cap is not None:
                print(f"[videoio] open idx={cam_idx} api={api}")
                return cap
    return None


def draw_landmarks(frame, lm):
    """Draw simple circles for each landmark on a frame in-place."""
    h, w = frame.shape[:2]
    for (x, y) in lm:
        cv2.circle(frame, (int(x * w), int(y * h)), 4, (0, 255, 0), -1)
