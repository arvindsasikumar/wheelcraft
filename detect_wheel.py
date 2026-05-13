"""
Phase 1: detect connected controllers and live-dump their state.

Run this with the wheel plugged in. It will:
  - list every joystick/controller pygame can see
  - pick the first one (or the one you choose) and stream its inputs to the terminal
  - print which axis/button/hat changed so you can map the wheel's physical controls

Press Ctrl+C to quit.
"""

import os
import sys
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame


def list_controllers() -> list[pygame.joystick.JoystickType]:
    pygame.init()
    pygame.joystick.init()
    count = pygame.joystick.get_count()
    sticks = [pygame.joystick.Joystick(i) for i in range(count)]
    for s in sticks:
        s.init()
    return sticks


def describe(stick: pygame.joystick.JoystickType) -> str:
    return (
        f"  name      : {stick.get_name()}\n"
        f"  guid      : {stick.get_guid()}\n"
        f"  axes      : {stick.get_numaxes()}\n"
        f"  buttons   : {stick.get_numbuttons()}\n"
        f"  hats      : {stick.get_numhats()}\n"
        f"  balls     : {stick.get_numballs()}"
    )


def stream(stick: pygame.joystick.JoystickType) -> None:
    n_axes = stick.get_numaxes()
    n_buttons = stick.get_numbuttons()
    n_hats = stick.get_numhats()

    last_axes = [None] * n_axes
    last_buttons = [None] * n_buttons
    last_hats = [None] * n_hats

    print(f"\nstreaming inputs from: {stick.get_name()}")
    print("move the wheel / press pedals / press buttons. ctrl+c to quit.\n")

    AXIS_DEADBAND = 0.02

    while True:
        pygame.event.pump()

        for i in range(n_axes):
            v = stick.get_axis(i)
            prev = last_axes[i]
            if prev is None or abs(v - prev) > AXIS_DEADBAND:
                print(f"  axis {i:>2}: {v:+.3f}")
                last_axes[i] = v

        for i in range(n_buttons):
            v = stick.get_button(i)
            if last_buttons[i] != v:
                state = "DOWN" if v else "up"
                print(f"  btn  {i:>2}: {state}")
                last_buttons[i] = v

        for i in range(n_hats):
            v = stick.get_hat(i)
            if last_hats[i] != v:
                print(f"  hat  {i:>2}: {v}")
                last_hats[i] = v

        time.sleep(0.01)


def main() -> int:
    sticks = list_controllers()
    if not sticks:
        print("no controllers detected. is the wheel plugged in?")
        return 1

    print(f"detected {len(sticks)} controller(s):\n")
    for i, s in enumerate(sticks):
        print(f"[{i}]")
        print(describe(s))
        print()

    choice = 0
    if len(sticks) > 1:
        raw = input(f"which one to stream? [0-{len(sticks) - 1}, default 0]: ").strip()
        if raw:
            choice = int(raw)

    try:
        stream(sticks[choice])
    except KeyboardInterrupt:
        print("\nbye.")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
