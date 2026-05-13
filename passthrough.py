"""
Phase 2: identity passthrough.

Read the real wheel via XInput, write its state to a virtual Xbox 360 controller
via ViGEmBus. No transformations yet — this just proves the pipeline works end to end.

After running:
  - the wheel is on XInput slot 0 (as before)
  - a NEW virtual Xbox 360 controller appears on slot 1+
  - games that read the virtual controller will see your wheel inputs mirrored

Ctrl+C to stop.
"""

import ctypes
import sys
import time
from ctypes import wintypes

import vgamepad as vg


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


XINPUT_BUTTON_TO_VG = {
    0x0001: vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,
    0x0002: vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
    0x0004: vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,
    0x0008: vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT,
    0x0010: vg.XUSB_BUTTON.XUSB_GAMEPAD_START,
    0x0020: vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
    0x0040: vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,
    0x0080: vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,
    0x0100: vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
    0x0200: vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
    0x1000: vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
    0x2000: vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
    0x4000: vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
    0x8000: vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
}


def find_real_wheel(XInputGetState) -> int | None:
    """Return the XInput slot of the first connected real controller, or None."""
    state = XINPUT_STATE()
    for i in range(4):
        if XInputGetState(i, ctypes.byref(state)) == 0:
            return i
    return None


def main() -> int:
    try:
        xinput = ctypes.WinDLL("XInput1_4.dll")
    except OSError:
        xinput = ctypes.WinDLL("xinput9_1_0.dll")

    XInputGetState = xinput.XInputGetState
    XInputGetState.argtypes = [wintypes.DWORD, ctypes.POINTER(XINPUT_STATE)]
    XInputGetState.restype = wintypes.DWORD

    real_slot = find_real_wheel(XInputGetState)
    if real_slot is None:
        print("no real XInput controller detected. plug in the wheel.")
        return 1
    print(f"reading real wheel from XInput slot {real_slot}")

    print("creating virtual Xbox 360 controller via ViGEmBus...")
    pad = vg.VX360Gamepad()
    pad.update()
    print("virtual pad created. it should appear on another XInput slot.")
    print("press Ctrl+C to stop.\n")

    state = XINPUT_STATE()
    last_print = 0.0

    while True:
        if XInputGetState(real_slot, ctypes.byref(state)) != 0:
            time.sleep(0.05)
            continue
        gp = state.Gamepad

        pad.left_joystick(x_value=gp.sThumbLX, y_value=gp.sThumbLY)
        pad.right_joystick(x_value=gp.sThumbRX, y_value=gp.sThumbRY)
        pad.left_trigger(value=gp.bLeftTrigger)
        pad.right_trigger(value=gp.bRightTrigger)

        for mask, vg_button in XINPUT_BUTTON_TO_VG.items():
            if gp.wButtons & mask:
                pad.press_button(button=vg_button)
            else:
                pad.release_button(button=vg_button)

        pad.update()

        now = time.monotonic()
        if now - last_print > 0.1:
            last_print = now
            sys.stdout.write(
                f"\rLX={gp.sThumbLX:+6d}  LT={gp.bLeftTrigger:3d}  "
                f"RT={gp.bRightTrigger:3d}  btns=0x{gp.wButtons:04x}    "
            )
            sys.stdout.flush()

        time.sleep(0.005)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nbye.")
