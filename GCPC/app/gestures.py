# -*- coding: utf-8 -*-
import math
import time
from collections import deque

WRIST = 0
THUMB_TIP = 4
INDEX_TIP = 8
MIDDLE_TIP = 12
RING_TIP = 16
PINKY_TIP = 20
INDEX_PIP = 6
MIDDLE_PIP = 10
RING_PIP = 14
PINKY_PIP = 18
INDEX_MCP = 5
MIDDLE_MCP = 9
RING_MCP = 13
PINKY_MCP = 17
THUMB_IP = 3
THUMB_MCP = 2


def _dist(a, b):
    """Compute Euclidean distance between two 2D points."""
    dx, dy = a[0] - b[0], a[1] - b[1]
    return (dx * dx + dy * dy) ** 0.5


def _angle(a, b, c):
    """Return angle ABC in radians for three 2D points."""
    ab = (a[0] - b[0], a[1] - b[1])
    cb = (c[0] - b[0], c[1] - b[1])
    dot = ab[0] * cb[0] + ab[1] * cb[1]
    nab = (ab[0] ** 2 + ab[1] ** 2) ** 0.5
    ncb = (cb[0] ** 2 + cb[1] ** 2) ** 0.5
    if nab * ncb == 0:
        return 0.0
    cosv = max(-1.0, min(1.0, dot / (nab * ncb)))
    return math.acos(cosv)


def finger_flexion(lm):
    """Estimate flexion level (0..1) for each finger based on landmarks."""

    def straight(tip, pip, mcp):
        ang = _angle(lm[tip], lm[pip], lm[mcp])
        return 1.0 - (ang / math.pi)

    return {
        "index": straight(INDEX_TIP, INDEX_PIP, INDEX_MCP),
        "middle": straight(MIDDLE_TIP, MIDDLE_PIP, MIDDLE_MCP),
        "ring": straight(RING_TIP, RING_PIP, RING_MCP),
        "pinky": straight(PINKY_TIP, PINKY_PIP, PINKY_MCP),
        "thumb": straight(THUMB_TIP, THUMB_IP, THUMB_MCP),
    }


class GestureState:
    """Tracks gesture-related state and emits gesture events from landmarks."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.last_emit_global = 0.0
        self.last_emit_per = {}
        self.wrist_hist = deque(maxlen=20)
        self.prev_pinch = False
        self.hold_latched = False
        self.hold_latched_middle = False
        self.pose_flags = {}

    def _can_emit(self, name, now_ms):
        """Check cooldown timers to decide if gesture can be emitted."""
        cd = float(self.cfg.get("cooldown_ms", 300))
        if now_ms - self.last_emit_global < cd:
            return False
        need = float(self.cfg.get("per_gesture_min_ms", {}).get(name, cd))
        if now_ms - self.last_emit_per.get(name, 0.0) < need:
            return False
        return True

    def _mark_emit(self, name, now_ms):
        """Record emission timestamps for cooldown tracking."""
        self.last_emit_global = now_ms
        self.last_emit_per[name] = now_ms

    def _detect_swipe(self, now_ms, swipe_window_ms, swipe_min_dx, swipe_max_ratio, swipe_min_speed):
        """Detect left/right swipe event from wrist trajectory history."""
        if len(self.wrist_hist) < 2:
            return None

        window_start = now_ms - swipe_window_ms
        oldest = self.wrist_hist[0]
        for ts, pt in self.wrist_hist:
            if ts >= window_start:
                oldest = (ts, pt)
                break

        ts0, p0 = oldest
        ts1, p1 = self.wrist_hist[-1]
        dt = max(1.0, ts1 - ts0)
        dx = p1[0] - p0[0]
        dy = p1[1] - p0[1]
        ratio = abs(dy) / max(abs(dx), 1e-4)
        speed = dx / (dt / 1000.0)

        if dx > swipe_min_dx and ratio <= swipe_max_ratio and speed >= swipe_min_speed:
            return "SWIPE_RIGHT"
        if -dx > swipe_min_dx and ratio <= swipe_max_ratio and -speed >= swipe_min_speed:
            return "SWIPE_LEFT"
        return None

    def update_and_classify(self, lm):
        """Update gesture state from landmarks and return detected gesture name."""
        now_ms = time.time() * 1000.0
        self.wrist_hist.append((now_ms, lm[WRIST]))

        flex = finger_flexion(lm)
        avg_other = (flex["middle"] + flex["ring"] + flex["pinky"]) / 3.0

        tu_thumb = float(self.cfg.get("thumbs_up_thumb_max_flex", 0.35))
        tu_others = float(self.cfg.get("thumbs_up_others_min_flex", 0.5))
        fist_thr = float(self.cfg.get("fist_threshold", 0.35))
        open_max = float(self.cfg.get("open_palm_max_flex", 0.35))

        is_fist = (
            flex["index"] > fist_thr
            and flex["middle"] > fist_thr
            and flex["ring"] > fist_thr
            and flex["pinky"] > fist_thr
        )

        pinch_d = _dist(lm[THUMB_TIP], lm[INDEX_TIP])
        middle_pinch_d = _dist(lm[THUMB_TIP], lm[MIDDLE_TIP])
        pinch_thr = float(self.cfg.get("pinch_threshold", 0.045))
        middle_pinch_thr = float(self.cfg.get("middle_pinch_threshold", pinch_thr))
        pinch = (pinch_d < pinch_thr) and not is_fist
        middle_pinch = (middle_pinch_d < middle_pinch_thr) and not is_fist

        is_open = (
            flex["index"] < open_max
            and flex["middle"] < open_max
            and flex["ring"] < open_max
            and flex["pinky"] < open_max
        )
        is_thumbs_up = flex["thumb"] < tu_thumb and avg_other > tu_others

        self.pose_flags = {
            "OPEN_PALM": bool(is_open),
            "FIST": bool(is_fist),
            "THUMBS_UP": bool(is_thumbs_up),
            "PINCH": bool(pinch),
            "PINCH_MIDDLE": bool(middle_pinch),
        }

        clutch = self.cfg.get("clutch", "none")
        ready = True if clutch == "none" else (pinch or middle_pinch)

        emit = None
        if not self.prev_pinch and pinch and ready and self._can_emit("PINCH_TAP", now_ms):
            emit = "PINCH_TAP"
        elif pinch and ready:
            if not self.hold_latched and self._can_emit("PINCH", now_ms):
                emit = "PINCH"
                self.hold_latched = True
        else:
            self.hold_latched = False

        if middle_pinch and ready:
            if not self.hold_latched_middle and self._can_emit("PINCH_MIDDLE", now_ms):
                emit = emit or "PINCH_MIDDLE"
                self.hold_latched_middle = True
        else:
            self.hold_latched_middle = False

        if is_fist and ready and self._can_emit("FIST", now_ms):
            emit = emit or "FIST"
        if is_thumbs_up and ready and self._can_emit("THUMBS_UP", now_ms):
            emit = emit or "THUMBS_UP"
        if is_open and ready and self._can_emit("OPEN_PALM", now_ms):
            emit = emit or "OPEN_PALM"

        swipe_window_ms = float(self.cfg.get("swipe_window_ms", 320))
        swipe_min_dx = float(self.cfg.get("swipe_min_dx", 0.1))
        swipe_max_ratio = float(self.cfg.get("swipe_max_dy_ratio", 0.6))
        swipe_min_speed = float(self.cfg.get("swipe_min_speed", 0.5))

        swipe_evt = self._detect_swipe(
            now_ms,
            swipe_window_ms,
            swipe_min_dx,
            swipe_max_ratio,
            swipe_min_speed,
        )
        if swipe_evt and self._can_emit(swipe_evt, now_ms):
            emit = emit or swipe_evt

        if emit:
            self._mark_emit(emit, now_ms)

        self.prev_pinch = pinch
        return emit
