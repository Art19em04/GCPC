# app/os_events.py
import sys
import ctypes
from ctypes import wintypes

if not sys.platform.startswith("win"):
    raise RuntimeError("Windows platform required for send_keys")

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

# --- Win types / fixes ---
if not hasattr(wintypes, "ULONG_PTR"):
    # Py3.12 на некоторых сборках не содержит ULONG_PTR
    wintypes.ULONG_PTR = (wintypes.WPARAM if hasattr(wintypes, "WPARAM")
                          else (ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8
                                else ctypes.c_ulong))

# --- constants ---
INPUT_MOUSE    = 0
INPUT_KEYBOARD = 1
INPUT_HARDWARE = 2

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP       = 0x0002
KEYEVENTF_SCANCODE    = 0x0008
# KEYEVENTF_UNICODE   = 0x0004  # нам не нужно

MAPVK_VK_TO_VSC = 0x0
MAPVK_VK_TO_VSC_EX = 0x4  # вернёт extended в старшем байте (0xE0/0xE1)

# --- structures (полный union для надёжности) ---
class MOUSEINPUT(ctypes.Structure):
    _fields_ = (("dx",          wintypes.LONG),
                ("dy",          wintypes.LONG),
                ("mouseData",   wintypes.DWORD),
                ("dwFlags",     wintypes.DWORD),
                ("time",        wintypes.DWORD),
                ("dwExtraInfo", wintypes.ULONG_PTR))

class KEYBDINPUT(ctypes.Structure):
    _fields_ = (("wVk",         wintypes.WORD),
                ("wScan",       wintypes.WORD),
                ("dwFlags",     wintypes.DWORD),
                ("time",        wintypes.DWORD),
                ("dwExtraInfo", wintypes.ULONG_PTR))

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = (("uMsg",  wintypes.DWORD),
                ("wParamL", wintypes.WORD),
                ("wParamH", wintypes.WORD))

class _INPUTunion(ctypes.Union):
    _fields_ = (("mi", MOUSEINPUT),
                ("ki", KEYBDINPUT),
                ("hi", HARDWAREINPUT))

class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = (("type", wintypes.DWORD),
                ("u",    _INPUTunion))

LPINPUT = ctypes.POINTER(INPUT)

user32.SendInput.argtypes = (wintypes.UINT, LPINPUT, ctypes.c_int)
user32.SendInput.restype  = wintypes.UINT

user32.MapVirtualKeyW.argtypes = (wintypes.UINT, wintypes.UINT)
user32.MapVirtualKeyW.restype  = wintypes.UINT

# --- VK map ---
VK = {
    "CTRL": 0x11, "CONTROL": 0x11,
    "SHIFT": 0x10,
    "ALT": 0x12, "MENU": 0x12,
    "WIN": 0x5B, "LWIN": 0x5B, "RWIN": 0x5C,
    "ENTER": 0x0D, "RETURN": 0x0D,
    "ESC": 0x1B, "ESCAPE": 0x1B,
    "TAB": 0x09, "SPACE": 0x20,
    "LEFT": 0x25, "UP": 0x26, "RIGHT": 0x27, "DOWN": 0x28,
    "C": 0x43, "V": 0x56, "X": 0x58, "Z": 0x5A,
}

def _vk_of(token: str) -> int:
    t = token.strip().upper()
    if t in VK:
        return VK[t]
    # одиночный символ → его VK (для латиницы совпадает с ASCII)
    if len(t) == 1:
        return ord(t)
    return 0  # неизвестный токен

def _scan_of_vk(vk: int):
    """
    Возвращает (scan_code, is_extended).
    MAPVK_VK_TO_VSC_EX (4) кладёт 0xE0/0xE1 в старший байт для extended-клавиш.
    """
    if vk == 0:
        return 0, False
    sc_ex = user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC_EX)
    if sc_ex == 0:
        # fallback: обычный режим
        sc = user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC)
        return sc & 0xFF, False
    ext = (sc_ex & 0xFF00) != 0
    return (sc_ex & 0xFF), bool(ext)

def _key_event_sc(scan_code: int, extended: bool, keyup: bool) -> INPUT:
    flags = KEYEVENTF_SCANCODE
    if extended:
        flags |= KEYEVENTF_EXTENDEDKEY
    if keyup:
        flags |= KEYEVENTF_KEYUP
    ki = KEYBDINPUT(wVk=0, wScan=scan_code, dwFlags=flags, time=0, dwExtraInfo=0)
    return INPUT(type=INPUT_KEYBOARD, ki=ki)

def _press_combo(tokens):
    # tokens: ["CTRL", "C"] и т.п.
    toks = [t for t in tokens if t]
    if not toks:
        return
    mods = toks[:-1]
    main = toks[-1]

    events = []

    # press modifiers
    for m in mods:
        vk = _vk_of(m)
        sc, ext = _scan_of_vk(vk)
        if sc == 0:
            continue
        events.append(_key_event_sc(sc, ext, keyup=False))

    # press main
    vk = _vk_of(main)
    sc, ext = _scan_of_vk(vk)
    if sc != 0:
        events.append(_key_event_sc(sc, ext, keyup=False))
        events.append(_key_event_sc(sc, ext, keyup=True))

    # release modifiers (reverse)
    for m in reversed(mods):
        vk = _vk_of(m)
        sc, ext = _scan_of_vk(vk)
        if sc == 0:
            continue
        events.append(_key_event_sc(sc, ext, keyup=True))

    if not events:
        return

    arr = (INPUT * len(events))(*events)
    sent = user32.SendInput(len(events), arr, ctypes.sizeof(INPUT))
    if sent != len(events):
        raise ctypes.WinError(ctypes.get_last_error())

def send_keys(tokens):
    """
    tokens: например ["CTRL","C"] либо ["CTRL","V"].
    Работает через SCANCODE + EXTENDEDKEY (для extended клавиш).
    """
    _press_combo(tokens)
