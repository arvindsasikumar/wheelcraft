"""
Fixed-duration wheel input capture.

Streams events as they happen AND accumulates min/max/range per axis,
which buttons were pressed at least once, and which hat positions were seen.
Prints a summary table at the end.

Usage: python -u capture_wheel.py [seconds=25]
"""

import os
import sys
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame


def main() -> int:
    duration = float(sys.argv[1]) if len(sys.argv) > 1 else 25.0

    pygame.init()
    pygame.joystick.init()
    if pygame.joystick.get_count() == 0:
        print("no controllers detected.", flush=True)
        return 1

    stick = pygame.joystick.Joystick(0)
    stick.init()

    n_axes = stick.get_numaxes()
    n_buttons = stick.get_numbuttons()
    n_hats = stick.get_numhats()

    print(f"capturing from: {stick.get_name()}", flush=True)
    print(f"axes={n_axes} buttons={n_buttons} hats={n_hats}", flush=True)
    print(f"duration: {duration:.0f}s — operate the wheel now\n", flush=True)

    last_axes = [None] * n_axes
    last_buttons = [0] * n_buttons
    last_hats = [(0, 0)] * n_hats

    axis_min = [float("inf")] * n_axes
    axis_max = [float("-inf")] * n_axes
    buttons_seen = set()
    hats_seen = [set() for _ in range(n_hats)]

    AXIS_DEADBAND = 0.05
    start = time.monotonic()

    while time.monotonic() - start < duration:
        pygame.event.pump()
        t = time.monotonic() - start

        for i in range(n_axes):
            v = stick.get_axis(i)
            if v < axis_min[i]:
                axis_min[i] = v
            if v > axis_max[i]:
                axis_max[i] = v
            prev = last_axes[i]
            if prev is None or abs(v - prev) > AXIS_DEADBAND:
                print(f"[{t:5.1f}s] axis {i}: {v:+.3f}", flush=True)
                last_axes[i] = v

        for i in range(n_buttons):
            v = stick.get_button(i)
            if last_buttons[i] != v:
                if v:
                    buttons_seen.add(i)
                    print(f"[{t:5.1f}s] btn  {i}: DOWN", flush=True)
                else:
                    print(f"[{t:5.1f}s] btn  {i}: up", flush=True)
                last_buttons[i] = v

        for i in range(n_hats):
            v = stick.get_hat(i)
            if last_hats[i] != v:
                hats_seen[i].add(v)
                print(f"[{t:5.1f}s] hat  {i}: {v}", flush=True)
                last_hats[i] = v

        time.sleep(0.01)

    print("\n" + "=" * 60, flush=True)
    print("SUMMARY", flush=True)
    print("=" * 60, flush=True)
    print("\naxis ranges (moved = range > 0.1):", flush=True)
    for i in range(n_axes):
        lo = axis_min[i] if axis_min[i] != float("inf") else 0.0
        hi = axis_max[i] if axis_max[i] != float("-inf") else 0.0
        rng = hi - lo
        marker = " <-- MOVED" if rng > 0.1 else ""
        print(f"  axis {i}: min={lo:+.3f}  max={hi:+.3f}  range={rng:.3f}{marker}", flush=True)

    print(f"\nbuttons pressed: {sorted(buttons_seen) if buttons_seen else 'none'}", flush=True)
    print(f"\nhat positions seen:", flush=True)
    for i in range(n_hats):
        print(f"  hat {i}: {sorted(hats_seen[i]) if hats_seen[i] else 'none'}", flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
