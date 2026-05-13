"""
Read the wheel directly via Windows XInput API (no SDL/pygame).
This is what real games use to read Xbox controllers.

Streams + summarizes for 30s. If steering doesn't show up here either,
it's a driver-level issue, not a pygame issue.
"""

import ctypes
import sys
import time
from ctypes import wintypes


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


XINPUT_BUTTONS = {
    0x0001: "DPAD_UP",
    0x0002: "DPAD_DOWN",
    0x0004: "DPAD_LEFT",
    0x0008: "DPAD_RIGHT",
    0x0010: "START",
    0x0020: "BACK",
    0x0040: "LSTICK",
    0x0080: "RSTICK",
    0x0100: "LB",
    0x0200: "RB",
    0x1000: "A",
    0x2000: "B",
    0x4000: "X",
    0x8000: "Y",
}


def main() -> int:
    duration = float(sys.argv[1]) if len(sys.argv) > 1 else 30.0

    try:
        xinput = ctypes.WinDLL("XInput1_4.dll")
    except OSError:
        xinput = ctypes.WinDLL("xinput9_1_0.dll")

    XInputGetState = xinput.XInputGetState
    XInputGetState.argtypes = [wintypes.DWORD, ctypes.POINTER(XINPUT_STATE)]
    XInputGetState.restype = wintypes.DWORD

    state = XINPUT_STATE()
    ERROR_SUCCESS = 0

    user_index = None
    for i in range(4):
        if XInputGetState(i, ctypes.byref(state)) == ERROR_SUCCESS:
            user_index = i
            break

    if user_index is None:
        print("no XInput controller detected.", flush=True)
        return 1

    print(f"reading XInput slot {user_index} for {duration:.0f}s", flush=True)
    print("operate the wheel now\n", flush=True)

    last = None
    lx_min = ly_min = rx_min = ry_min = 32767
    lx_max = ly_max = rx_max = ry_max = -32768
    lt_min = rt_min = 255
    lt_max = rt_max = 0
    buttons_seen: set[str] = set()

    start = time.monotonic()
    while time.monotonic() - start < duration:
        if XInputGetState(user_index, ctypes.byref(state)) != ERROR_SUCCESS:
            time.sleep(0.05)
            continue

        gp = state.Gamepad
        t = time.monotonic() - start

        lx_min, lx_max = min(lx_min, gp.sThumbLX), max(lx_max, gp.sThumbLX)
        ly_min, ly_max = min(ly_min, gp.sThumbLY), max(ly_max, gp.sThumbLY)
        rx_min, rx_max = min(rx_min, gp.sThumbRX), max(rx_max, gp.sThumbRX)
        ry_min, ry_max = min(ry_min, gp.sThumbRY), max(ry_max, gp.sThumbRY)
        lt_min, lt_max = min(lt_min, gp.bLeftTrigger), max(lt_max, gp.bLeftTrigger)
        rt_min, rt_max = min(rt_min, gp.bRightTrigger), max(rt_max, gp.bRightTrigger)

        for mask, name in XINPUT_BUTTONS.items():
            if gp.wButtons & mask:
                buttons_seen.add(name)

        snap = (
            gp.wButtons,
            gp.bLeftTrigger // 8,
            gp.bRightTrigger // 8,
            gp.sThumbLX // 1024,
            gp.sThumbLY // 1024,
            gp.sThumbRX // 1024,
            gp.sThumbRY // 1024,
        )
        if snap != last:
            last = snap
            print(
                f"[{t:5.1f}s] LX={gp.sThumbLX:+6d} LY={gp.sThumbLY:+6d} "
                f"RX={gp.sThumbRX:+6d} RY={gp.sThumbRY:+6d} "
                f"LT={gp.bLeftTrigger:3d} RT={gp.bRightTrigger:3d} "
                f"btns=0x{gp.wButtons:04x}",
                flush=True,
            )

        time.sleep(0.01)

    print("\n" + "=" * 60, flush=True)
    print("SUMMARY (XInput raw)", flush=True)
    print("=" * 60, flush=True)
    print(f"  LX: min={lx_min:+6d} max={lx_max:+6d} range={lx_max-lx_min}", flush=True)
    print(f"  LY: min={ly_min:+6d} max={ly_max:+6d} range={ly_max-ly_min}", flush=True)
    print(f"  RX: min={rx_min:+6d} max={rx_max:+6d} range={rx_max-rx_min}", flush=True)
    print(f"  RY: min={ry_min:+6d} max={ry_max:+6d} range={ry_max-ry_min}", flush=True)
    print(f"  LT: min={lt_min:3d} max={lt_max:3d} range={lt_max-lt_min}", flush=True)
    print(f"  RT: min={rt_min:3d} max={rt_max:3d} range={rt_max-rt_min}", flush=True)
    print(f"  buttons seen: {sorted(buttons_seen) if buttons_seen else 'none'}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
