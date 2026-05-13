"""XInput ctypes wrapper. Reads gamepad state from a numbered slot (0..3)."""

import ctypes
from ctypes import wintypes
from dataclasses import dataclass


class XINPUT_GAMEPAD(ctypes.Structure):
    _fields_ = [
        ("wButtons", wintypes.WORD),
        ("bLeftTrigger", ctypes.c_ubyte),
        ("bRightTrigger", ctypes.c_ubyte),
        ("sThumbLX", ctypes.c_short),
        ("sThumbLY", ctypes.c_short),
        ("sThumbRX", ctypes.c_short),
        ("sThumbRY", ctypes.c_short),
    ]


class XINPUT_STATE(ctypes.Structure):
    _fields_ = [
        ("dwPacketNumber", wintypes.DWORD),
        ("Gamepad", XINPUT_GAMEPAD),
    ]


@dataclass
class GamepadState:
    buttons: int
    lt: int
    rt: int
    lx: int
    ly: int
    rx: int
    ry: int

    @classmethod
    def zero(cls) -> "GamepadState":
        return cls(0, 0, 0, 0, 0, 0, 0)


_XINPUT_BUTTON_BITS = {
    "DPAD_UP": 0x0001,
    "DPAD_DOWN": 0x0002,
    "DPAD_LEFT": 0x0004,
    "DPAD_RIGHT": 0x0008,
    "START": 0x0010,
    "BACK": 0x0020,
    "LSTICK": 0x0040,
    "RSTICK": 0x0080,
    "LB": 0x0100,
    "RB": 0x0200,
    "A": 0x1000,
    "B": 0x2000,
    "X": 0x4000,
    "Y": 0x8000,
}


def button_names(mask: int) -> list[str]:
    return [name for name, bit in _XINPUT_BUTTON_BITS.items() if mask & bit]


def button_bit(name: str) -> int:
    return _XINPUT_BUTTON_BITS[name]


ALL_BUTTON_NAMES: list[str] = list(_XINPUT_BUTTON_BITS.keys())


class XInputReader:
    """Read a numbered XInput slot."""

    def __init__(self) -> None:
        try:
            self._dll = ctypes.WinDLL("XInput1_4.dll")
        except OSError:
            self._dll = ctypes.WinDLL("xinput9_1_0.dll")
        self._dll.XInputGetState.argtypes = [wintypes.DWORD, ctypes.POINTER(XINPUT_STATE)]
        self._dll.XInputGetState.restype = wintypes.DWORD
        self._state = XINPUT_STATE()

    def first_connected_slot(self) -> int | None:
        for i in range(4):
            if self._dll.XInputGetState(i, ctypes.byref(self._state)) == 0:
                return i
        return None

    def read(self, slot: int) -> GamepadState | None:
        if self._dll.XInputGetState(slot, ctypes.byref(self._state)) != 0:
            return None
        g = self._state.Gamepad
        return GamepadState(
            buttons=g.wButtons,
            lt=g.bLeftTrigger,
            rt=g.bRightTrigger,
            lx=g.sThumbLX,
            ly=g.sThumbLY,
            rx=g.sThumbRX,
            ry=g.sThumbRY,
        )
