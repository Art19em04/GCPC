"""Camera and drawing helpers."""

import platform
import subprocess
from typing import Iterable

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


def _backend_name(api: int) -> str:
    names = {
        getattr(cv2, "CAP_MSMF", None): "MSMF",
        getattr(cv2, "CAP_DSHOW", None): "DSHOW",
        getattr(cv2, "CAP_ANY", None): "ANY",
    }
    return names.get(api, str(api))


def _unique_indices(indices: Iterable[int]) -> tuple[int, ...]:
    result = []
    for index in indices:
        if index not in result:
            result.append(index)
    return tuple(result)


def _device_index_options(device_names: Iterable[str]) -> tuple[int, ...]:
    return tuple(range(len(tuple(device_names))))


def camera_device_names() -> tuple[str, ...]:
    """Return OS-level camera device names when Windows exposes them."""
    if platform.system() != "Windows":
        return ()
    command = (
        "$ErrorActionPreference = 'SilentlyContinue'; "
        "Get-CimInstance Win32_PnPEntity | "
        "Where-Object {"
        "($_.PNPClass -eq 'Camera' -or $_.PNPClass -eq 'Image') -and $_.Name"
        "} | ForEach-Object { $_.Name }"
    )
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=1.5,
            creationflags=creation_flags,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ()
    names = []
    for line in completed.stdout.splitlines():
        name = line.strip()
        if name and name not in names:
            names.append(name)
    return tuple(names)


def available_camera_indices(
    device_names: Iterable[str] | None = None,
) -> tuple[int, ...]:
    """Return cheap OS-derived indices without opening camera devices."""
    names = camera_device_names() if device_names is None else tuple(device_names)
    return _device_index_options(names)


def probe_camera_indices(width: int = 640, height: int = 360) -> tuple[int, ...]:
    """Actively probe common OpenCV indices; use only on explicit refresh."""
    found = []
    for cam_idx in _PROBE_RANGE:
        for api in _BACKENDS:
            cap = _open_with_backend(cam_idx, api, width, height)
            if cap is None:
                continue
            cap.release()
            found.append(cam_idx)
            break
    return tuple(found)


def camera_index_options(
    idx: int,
    available_indices: Iterable[int],
    last_working_idx: int | None = None,
) -> tuple[int, ...]:
    """Build a stable list of user-selectable camera indices."""
    candidates = [idx]
    candidates.extend(available_indices)
    if last_working_idx is not None:
        candidates.append(last_working_idx)
    return _unique_indices(candidates)


def _candidate_indices(
    idx: int,
    preferred_idx: int | None = None,
    prefer_configured: bool = False,
) -> tuple[int, ...]:
    configured = []
    if idx == -1:
        configured.extend((-1, *_PROBE_RANGE))
    else:
        configured.append(idx)
    preferred = []
    if preferred_idx is not None:
        preferred.append(preferred_idx)
    candidates = []
    if prefer_configured:
        candidates.extend(configured)
        candidates.extend(preferred)
    else:
        candidates.extend(preferred)
        candidates.extend(configured)
    return _unique_indices(candidates)


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


def open_camera(
    idx: int,
    w: int,
    h: int,
    preferred_idx: int | None = None,
    prefer_configured: bool = False,
):
    """Open a camera with saved last-working fallback across APIs."""
    for cam_idx in _candidate_indices(idx, preferred_idx, prefer_configured):
        for api in _BACKENDS:
            cap = _open_with_backend(cam_idx, api, w, h)
            if cap is not None:
                print(f"[videoio] open idx={cam_idx} api={_backend_name(api)}")
                return cap, cam_idx
    return None, None


def draw_landmarks(frame, lm):
    """Draw simple circles for each landmark on a frame in-place."""
    h, w = frame.shape[:2]
    for (x, y) in lm:
        cv2.circle(frame, (int(x * w), int(y * h)), 4, (0, 255, 0), -1)
