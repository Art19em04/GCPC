import cv2


HAND_CONNECTIONS = (
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 4),
    (0, 5),
    (5, 6),
    (6, 7),
    (7, 8),
    (5, 9),
    (9, 10),
    (10, 11),
    (11, 12),
    (9, 13),
    (13, 14),
    (14, 15),
    (15, 16),
    (13, 17),
    (17, 18),
    (18, 19),
    (19, 20),
    (0, 17),
)


def _draw_hand_overlay(frame, hand, color=(0, 255, 255)):
    x0, y0, x1, y1 = hand.rect_xyxy
    width = max(1, x1 - x0)
    height = max(1, y1 - y0)
    pts = []
    for (nx, ny, _nz) in hand.landmarks:
        px = int(x0 + nx * width)
        py = int(y0 + ny * height)
        pts.append((px, py))
    for a, b in HAND_CONNECTIONS:
        if 0 <= a < len(pts) and 0 <= b < len(pts):
            cv2.line(frame, pts[a], pts[b], color, 2, cv2.LINE_AA)
    for (px, py) in pts:
        cv2.circle(frame, (px, py), 3, color, -1, lineType=cv2.LINE_AA)


def draw_hud(frame, fps, clutch_state, decision, e2e_ms, hand=None):
    y = 24
    cv2.putText(frame, f"FPS: {fps:.1f}", (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    y += 24
    cv2.putText(frame, f"Clutch: {clutch_state.name}", (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
    y += 24
    cv2.putText(
        frame,
        f"Gesture: {decision.g.name} conf={decision.confidence:.2f} dur={decision.duration_ms}ms",
        (10, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 200, 255),
        2,
    )
    y += 24
    cv2.putText(frame, f"e2e p: {e2e_ms:.1f} ms", (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
    if hand is not None:
        _draw_hand_overlay(frame, hand)
    return frame
