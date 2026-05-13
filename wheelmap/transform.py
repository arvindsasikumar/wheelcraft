"""Apply a Profile to a GamepadState."""

from .profile import AxisConfig, Profile
from .xinput import GamepadState, button_bit


def _unipolar_remap(x: float, cfg: AxisConfig) -> float:
    """x in [0, 1], returns [0, 1]."""
    if cfg.invert:
        x = 1.0 - x
    inner = cfg.inner_deadzone_pct / 100
    outer = cfg.outer_saturation_pct / 100
    out_min = cfg.output_min_pct / 100
    out_max = cfg.output_max_pct / 100

    if x <= inner:
        return 0.0
    if x >= outer:
        return out_max
    normalized = (x - inner) / max(outer - inner, 1e-9)
    shaped = normalized ** cfg.curve_power
    return out_min + shaped * (out_max - out_min)


def _bipolar_remap(x: float, cfg: AxisConfig) -> float:
    """x in [-1, 1], returns [-1, 1]. Curve applied symmetrically."""
    if cfg.invert:
        x = -x
    sign = 1.0 if x >= 0 else -1.0
    mag = abs(x)
    inner = cfg.inner_deadzone_pct / 100
    outer = cfg.outer_saturation_pct / 100
    out_min = cfg.output_min_pct / 100
    out_max = cfg.output_max_pct / 100

    if mag <= inner:
        return 0.0
    if mag >= outer:
        return sign * out_max
    normalized = (mag - inner) / max(outer - inner, 1e-9)
    shaped = normalized ** cfg.curve_power
    out_mag = out_min + shaped * (out_max - out_min)
    return sign * out_mag


_BUTTON_BITS = {
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


def _remap_buttons(mask: int, remap: dict[str, str]) -> int:
    out = 0
    for name, bit in _BUTTON_BITS.items():
        if mask & bit:
            target_name = remap.get(name, name)
            target_bit = _BUTTON_BITS.get(target_name)
            if target_bit is not None:
                out |= target_bit
    return out


def apply_profile(real: GamepadState, profile: Profile) -> GamepadState:
    lx_norm = max(-1.0, min(1.0, real.lx / 32767.0))
    lx_out = _bipolar_remap(lx_norm, profile.steering) * 32767
    lx_int = int(round(max(-32768, min(32767, lx_out))))

    lt_out = _unipolar_remap(real.lt / 255.0, profile.brake) * 255
    rt_out = _unipolar_remap(real.rt / 255.0, profile.throttle) * 255
    lt_int = int(round(max(0, min(255, lt_out))))
    rt_int = int(round(max(0, min(255, rt_out))))

    buttons_out = _remap_buttons(real.buttons, profile.button_remap)

    return GamepadState(
        buttons=buttons_out,
        lt=lt_int,
        rt=rt_int,
        lx=lx_int,
        ly=real.ly,
        rx=real.rx,
        ry=real.ry,
    )
