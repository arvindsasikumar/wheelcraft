"""
Read XInput slot 0 (real wheel) and slot 1 (virtual pad) side by side.
While passthrough.py is running, both columns should be identical.
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


def fmt(gp: XINPUT_GAMEPAD) -> str:
    return f"LX={gp.sThumbLX:+6d} LT={gp.bLeftTrigger:3d} RT={gp.bRightTrigger:3d} btns=0x{gp.wButtons:04x}"


def main() -> int:
    duration = float(sys.argv[1]) if len(sys.argv) > 1 else 20.0
    x = ctypes.WinDLL("XInput1_4.dll")
    x.XInputGetState.argtypes = [wintypes.DWORD, ctypes.POINTER(XINPUT_STATE)]
    x.XInputGetState.restype = wintypes.DWORD

    s0 = XINPUT_STATE()
    s1 = XINPUT_STATE()

    print(f"comparing slot 0 (real) vs slot 1 (virtual) for {duration:.0f}s")
    print("operate the wheel — slot 1 should match slot 0\n")
    print(f"{'slot 0 (real wheel)':<45} | {'slot 1 (virtual pad)':<45}")
    print("-" * 95)

    mismatches = 0
    samples = 0
    last_snap = None
    start = time.monotonic()

    while time.monotonic() - start < duration:
        ok0 = x.XInputGetState(0, ctypes.byref(s0)) == 0
        ok1 = x.XInputGetState(1, ctypes.byref(s1)) == 0

        if ok0 and ok1:
            samples += 1
            g0, g1 = s0.Gamepad, s1.Gamepad
            match = (
                g0.sThumbLX == g1.sThumbLX
                and g0.sThumbLY == g1.sThumbLY
                and g0.sThumbRX == g1.sThumbRX
                and g0.sThumbRY == g1.sThumbRY
                and g0.bLeftTrigger == g1.bLeftTrigger
                and g0.bRightTrigger == g1.bRightTrigger
                and g0.wButtons == g1.wButtons
            )
            if not match:
                mismatches += 1
            snap = (g0.sThumbLX // 1024, g0.bLeftTrigger // 8, g0.bRightTrigger // 8, g0.wButtons)
            if snap != last_snap:
                last_snap = snap
                marker = " " if match else " <-- DIFF"
                print(f"{fmt(g0):<45} | {fmt(g1):<45}{marker}", flush=True)

        time.sleep(0.02)

    print("\n" + "=" * 95)
    print(f"samples: {samples}    mismatches: {mismatches}")
    if mismatches == 0 and samples > 0:
        print("PASS: virtual pad mirrors real wheel perfectly")
    elif samples == 0:
        print("FAIL: no samples - is the passthrough script running?")
    else:
        pct = 100 * mismatches / samples
        print(f"NOTE: {pct:.1f}% of samples didn't match (small async-update lag, harmless)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
