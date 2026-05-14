"""
Background thread that reads the wheel, applies the active profile,
writes to the virtual pad, and stores the latest state for the UI.
"""

import threading
import time
from dataclasses import asdict, dataclass

import vgamepad as vg

from .profile import Profile
from .transform import apply_profile
from .xinput import (
    ALL_BUTTON_NAMES,
    GamepadState,
    XInputReader,
    button_names,
)


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


@dataclass
class Snapshot:
    real: GamepadState
    virtual: GamepadState
    real_button_names: list[str]
    virtual_button_names: list[str]
    real_slot: int
    virtual_slot: int | None
    hz: float
    connected: bool
    profile_name: str


class WheelPipeline:
    """Owns the wheel-read / pad-write loop and the active profile reference."""

    def __init__(self, profile: Profile) -> None:
        self._reader = XInputReader()
        self._pad = vg.VX360Gamepad()
        self._pad.update()
        self._real_slot = 0
        self._virtual_slot: int | None = None
        self._profile = profile
        self._latest = Snapshot(
            real=GamepadState.zero(),
            virtual=GamepadState.zero(),
            real_button_names=[],
            virtual_button_names=[],
            real_slot=0,
            virtual_slot=None,
            hz=0.0,
            connected=False,
            profile_name=profile.name,
        )
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="wheel-pipeline", daemon=True)

    @property
    def profile(self) -> Profile:
        return self._profile

    def set_profile(self, profile: Profile) -> None:
        self._profile = profile

    def start(self) -> None:
        # Locate our own virtual pad by writing a sentinel value to it and
        # reading XInput slots back. `vgamepad.get_index()` is unreliable
        # (returns wrong slot in some Windows + ViGEmBus states), and naively
        # picking first_connected_slot() picks up our own pad and creates a
        # read/write feedback loop.
        virtual_slot = self._detect_virtual_slot()

        real_slot = None
        for i in range(4):
            if i == virtual_slot:
                continue
            if self._reader.read(i) is not None:
                real_slot = i
                break

        if real_slot is None:
            raise RuntimeError("no real XInput controller detected; plug in the wheel")

        self._real_slot = real_slot
        self._virtual_slot = virtual_slot
        self._thread.start()

    def _detect_virtual_slot(self) -> int | None:
        """Write a sentinel LX value to our virtual pad, then scan XInput slots
        to find the one that echoes it back. Reset to neutral after."""
        SENTINEL = 12345  # arbitrary, unlikely to occur naturally at rest
        self._pad.left_joystick(x_value=SENTINEL, y_value=0)
        self._pad.update()
        time.sleep(0.15)  # let the write propagate to XInput

        detected: int | None = None
        for i in range(4):
            s = self._reader.read(i)
            if s is not None and s.lx == SENTINEL:
                detected = i
                break

        # Reset pad to neutral so we don't bleed the sentinel to games
        self._pad.left_joystick(x_value=0, y_value=0)
        self._pad.update()
        return detected

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2)

    def _discover_virtual_slot(self, exclude: int) -> int | None:
        for i in range(4):
            if i == exclude:
                continue
            if self._reader.read(i) is not None:
                return i
        return None

    def _write_pad(self, state: GamepadState) -> None:
        self._pad.left_joystick(x_value=state.lx, y_value=state.ly)
        self._pad.right_joystick(x_value=state.rx, y_value=state.ry)
        self._pad.left_trigger(value=state.lt)
        self._pad.right_trigger(value=state.rt)
        for mask, vg_button in XINPUT_BUTTON_TO_VG.items():
            if state.buttons & mask:
                self._pad.press_button(button=vg_button)
            else:
                self._pad.release_button(button=vg_button)
        self._pad.update()

    def _run(self) -> None:
        period = 1 / 200
        tick = 0
        hz_window_start = time.monotonic()
        hz = 0.0

        while not self._stop.is_set():
            loop_start = time.monotonic()
            real = self._reader.read(self._real_slot)
            connected = real is not None
            if real is None:
                real = GamepadState.zero()

            profile = self._profile
            transformed = apply_profile(real, profile)
            self._write_pad(transformed)

            if self._virtual_slot is None:
                self._virtual_slot = self._discover_virtual_slot(exclude=self._real_slot)
            virtual = (
                self._reader.read(self._virtual_slot)
                if self._virtual_slot is not None
                else None
            ) or GamepadState.zero()

            tick += 1
            if tick % 50 == 0:
                now = time.monotonic()
                hz = 50 / max(now - hz_window_start, 1e-6)
                hz_window_start = now

            with self._lock:
                self._latest = Snapshot(
                    real=real,
                    virtual=virtual,
                    real_button_names=button_names(real.buttons),
                    virtual_button_names=button_names(virtual.buttons),
                    real_slot=self._real_slot,
                    virtual_slot=self._virtual_slot,
                    hz=hz,
                    connected=connected,
                    profile_name=profile.name,
                )

            elapsed = time.monotonic() - loop_start
            sleep_for = period - elapsed
            if sleep_for > 0:
                time.sleep(sleep_for)

    def snapshot_dict(self) -> dict:
        with self._lock:
            s = self._latest
        return {
            "real": asdict(s.real),
            "virtual": asdict(s.virtual),
            "real_button_names": s.real_button_names,
            "virtual_button_names": s.virtual_button_names,
            "real_slot": s.real_slot,
            "virtual_slot": s.virtual_slot,
            "hz": round(s.hz, 1),
            "connected": s.connected,
            "all_buttons": ALL_BUTTON_NAMES,
            "profile_name": s.profile_name,
        }
