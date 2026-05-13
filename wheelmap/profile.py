"""Profile schema. Pydantic for validation + JSON round-tripping."""

from pydantic import BaseModel, Field

from .xinput import ALL_BUTTON_NAMES


class AxisConfig(BaseModel):
    """
    Configuration for a single axis. Applied symmetrically for bipolar axes
    (steering) and from low-to-high for unipolar axes (pedals).

    All *_pct fields are 0..100 percent of the axis range.

    Pipeline (for input x in [0, 1] magnitude):
        1. if |x| < inner_deadzone_pct: output is 0
        2. if |x| > outer_saturation_pct: magnitude is output_max_pct
        3. else: normalize to [0, 1], raise to curve_power, scale into
           [output_min_pct, output_max_pct]
        4. apply invert (negate before everything for bipolar)
    """

    inner_deadzone_pct: float = Field(0, ge=0, le=99)
    outer_saturation_pct: float = Field(100, ge=1, le=100)
    output_min_pct: float = Field(0, ge=0, le=100)
    output_max_pct: float = Field(100, ge=0, le=100)
    curve_power: float = Field(1.0, ge=0.1, le=4.0)
    invert: bool = False


class Profile(BaseModel):
    name: str
    steering: AxisConfig = Field(default_factory=AxisConfig)
    brake: AxisConfig = Field(default_factory=AxisConfig)
    throttle: AxisConfig = Field(default_factory=AxisConfig)
    button_remap: dict[str, str] = Field(default_factory=dict)

    @staticmethod
    def default(name: str = "default") -> "Profile":
        return Profile(
            name=name,
            steering=AxisConfig(),
            brake=AxisConfig(),
            throttle=AxisConfig(),
            button_remap={b: b for b in ALL_BUTTON_NAMES},
        )
