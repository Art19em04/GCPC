import sys, subprocess, time, platform

# Key mapping: list like ["CTRL","C"] → platform-specific synth

def send_keys(keys):
    sysname = platform.system().lower()
    if "windows" in sysname:
        return _win_send(keys)
    elif "darwin" in sysname:
        try:
            return _mac_quartz(keys)
        except Exception:
            return _mac_osascript(keys)
    else:
        # Assume Linux
        if _is_wayland():
            return _linux_ydotool(keys) or _linux_xdotool(keys)
        else:
            return _linux_xdotool(keys)

def _is_wayland():
    import os
    return os.environ.get("XDG_SESSION_TYPE","").lower() == "wayland"

# --- Windows via SendInput ---
def _win_send(keys):
    import ctypes
    from ctypes import wintypes

    VK = {
        "CTRL": 0x11, "ALT": 0x12, "SHIFT": 0x10,
        "C": 0x43, "V": 0x56, "X": 0x58, "Z": 0x5A,
    }

    INPUT_KEYBOARD = 1
    KEYEVENTF_KEYUP = 0x0002

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", wintypes.WORD),
                    ("wScan", wintypes.WORD),
                    ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD),
                    ("dwExtraInfo", wintypes.ULONG_PTR)]

    class INPUT(ctypes.Structure):
        _fields_ = [("type", wintypes.DWORD),
                    ("ki", KEYBDINPUT)]

    SendInput = ctypes.windll.user32.SendInput

    def key_event(vk, down=True):
        inp = INPUT()
        inp.type = INPUT_KEYBOARD
        inp.ki = KEYBDINPUT(VK.get(vk, 0), 0, 0 if down else KEYEVENTF_KEYUP, 0, 0)
        SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))

    mods = [k for k in keys if k in ("CTRL","ALT","SHIFT")]
    rest = [k for k in keys if k not in mods]
    # press mods
    for m in mods:
        key_event(m, True)
    for r in rest:
        key_event(r, True)
        key_event(r, False)
    for m in reversed(mods):
        key_event(m, False)
    return True

# --- macOS Quartz ---
def _mac_quartz(keys):
    from Quartz import CGEventCreateKeyboardEvent, CGEventPost, kCGAnnotatedSessionEventTap, kCGEventFlagMaskShift, kCGEventFlagMaskControl, kCGEventFlagMaskAlternate
    import Quartz
    import AppKit

    # Map simple ASCII to virtual keycodes
    VKEY = {
        "C": 8, "V": 9, "X": 7, "Z": 6,
    }
    mods = [k for k in keys if k in ("CTRL","ALT","SHIFT")]
    rest = [k for k in keys if k not in mods]
    flags = 0
    if "SHIFT" in mods: flags |= kCGEventFlagMaskShift
    if "CTRL" in mods: flags |= kCGEventFlagMaskControl
    if "ALT" in mods: flags |= kCGEventFlagMaskAlternate

    for r in rest:
        ev_down = CGEventCreateKeyboardEvent(None, VKEY.get(r, 0), True)
        ev_up   = CGEventCreateKeyboardEvent(None, VKEY.get(r, 0), False)
        if flags:
            Quartz.CGEventSetFlags(ev_down, flags)
            Quartz.CGEventSetFlags(ev_up, flags)
        CGEventPost(kCGAnnotatedSessionEventTap, ev_down)
        CGEventPost(kCGAnnotatedSessionEventTap, ev_up)
    return True

# macOS fallback with osascript
def _mac_osascript(keys):
    apples = []
    mods = [k for k in keys if k in ("CTRL","ALT","SHIFT")]
    rest = [k for k in keys if k not in mods]
    modmap = {"CTRL":"control down", "ALT":"option down", "SHIFT":"shift down"}
    for r in rest:
        mods_clause = " using {" + ", ".join(modmap[m] for m in mods) + "}" if mods else ""
        apples.append(f'tell application "System Events" to keystroke "{r.lower()}"{mods_clause}')
    script = " & ".join(f'"{a}"' for a in apples)
    cmd = f'osascript -e {script}'
    subprocess.call(cmd, shell=True)
    return True

# Linux X11
def _linux_xdotool(keys):
    # convert to xdotool syntax
    kmap = {"CTRL":"ctrl", "ALT":"alt", "SHIFT":"shift"}
    seq = []
    for k in keys:
        if k in kmap:
            seq.append(kmap[k])
        else:
            seq.append(k.lower())
    combo = "+".join(seq)
    try:
        subprocess.check_call(["xdotool", "key", combo])
        return True
    except Exception:
        return False

# Linux Wayland
def _linux_ydotool(keys):
    combo = []
    kmap = {"CTRL":"leftctrl", "ALT":"leftalt", "SHIFT":"leftshift"}
    for k in keys:
        if k in kmap:
            combo.append(kmap[k])
        else:
            combo.append(k.lower())
    try:
        subprocess.check_call(["ydotool", "key"] + combo)
        return True
    except Exception:
        return False
