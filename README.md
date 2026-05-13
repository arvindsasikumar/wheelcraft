# wheelcraft

A Windows tool that reads a racing wheel via XInput, applies per-profile
transformations (deadzones, output floor/ceiling, curve power, button remap),
and emits the result as a virtual Xbox 360 controller via ViGEmBus. Includes
a browser-based live visualizer and profile editor served at `localhost:8765`.

## Quick start (running from source)

Prerequisites:
- Windows 10 or 11
- Python 3.11 from [python.org](https://www.python.org/downloads/) (tick "Add to PATH")
- [ViGEmBus 1.22.0](https://github.com/nefarius/ViGEmBus/releases/download/v1.22.0/ViGEmBus_1.22.0_x64_x86_arm64.exe)
  installed (one-time)
- An XInput-compatible wheel plugged in

Then:

```cmd
git clone https://github.com/<you>/wheelcraft.git
cd wheelcraft
run.bat
```

`run.bat` auto-creates a Python virtualenv on first run and installs
dependencies. After that it just starts the server and opens the browser at
`http://localhost:8765`.

## What you see in the UI

- **Live input panel** — a wheel viz that rotates as you turn yours, pedal
  bars, button grid, and a side-by-side "real → virtual" raw value table.
- **Per-axis editor** for steering, brake, throttle: input deadzone, input
  saturation, output floor (jump past games' in-game deadzone), output ceiling,
  curve power, invert. Live curve preview with input dot.
- **Button remap matrix** mapping each physical XInput button to a virtual one.
- **Profiles**: dropdown + save/new/delete. Edits apply live (no save needed
  to test); save persists to disk. Profiles live in
  `%APPDATA%\wheelcraft\profiles\` when running the packaged exe, or in
  `./profiles/` when running from source.

## In-game setup

When wheelcraft is running you'll have **two** XInput controllers visible to
games: slot 1 = your real wheel, slot 2 = the virtual pad with your profile
applied. Pick **Controller 2** in your game's controller settings, or the wheel
will bypass your tuning.

## Distributing

Two paths:

### Source distribution
Zip the repo (excluding `.venv`, `dist`, `build`, `.git`) and send. Recipient
installs Python + ViGEmBus, then runs `run.bat`.

### Single installer (recommended)
Build a Windows installer that bundles everything:

```cmd
build.bat                         REM creates dist\wheelcraft\
cd installer
fetch_vendor.bat                  REM downloads ViGEmBus into vendor\
REM Open wheelcraft.iss in Inno Setup and Compile
REM Output: installer\Output\wheelcraft-setup.exe
```

Recipient runs `wheelcraft-setup.exe` → it installs wheelcraft, installs ViGEmBus
if needed, creates shortcuts. One click.

## Architecture

```
real wheel  -> XInputGetState(slot 0)
            -> apply_profile (deadzones, curves, output floor/ceiling, button remap)
            -> vgamepad VX360Gamepad.update()  ===  ViGEmBus virtual Xbox 360 pad on slot 1
            ->        game reads the virtual pad
            -> WebSocket /live broadcasts live state to the browser UI ~60 Hz
```

The reader/writer loop runs at 200 Hz. The browser UI is a single static page
talking to a FastAPI WebSocket. All transformations are computed in Python on
the server side; the JS curve preview mirrors the math for live visualization.
