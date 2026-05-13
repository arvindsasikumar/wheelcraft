# CLAUDE.md

Project context for AI agents working on wheelcraft. Read this before touching
anything non-obvious.

## What this is

A Windows tool that reads a racing wheel via the XInput API, applies
user-configurable transformations (input deadzone, input saturation, output
floor, output ceiling, curve power, button remap, invert) according to the
active profile, and emits the transformed state as a virtual Xbox 360
controller via ViGEmBus. Games read the virtual pad and see the tuned input.

A FastAPI server hosts a single-page browser UI at `http://localhost:8765`
with live visualization and the profile editor.

Public repo: <https://github.com/arvindsasikumar/wheelcraft>.

## Data flow

```
real wheel → XInputGetState(slot 0)
          → apply_profile (wheelmap/transform.py)
          → vgamepad.VX360Gamepad.update()   ← writes to ViGEmBus virtual pad (slot 1)
                                              games read this
          ↓ (also)
          → Snapshot stored in pipeline._latest (thread-safe via _lock)
          → WebSocket /live broadcasts ~60 Hz to the browser UI
```

The read → transform → write → snapshot loop runs at ~200 Hz in a daemon
thread (`wheelmap/pipeline.py::WheelPipeline._run`). The browser UI mirrors
the transformation math in JS (`static/app.js`) for live curve preview.

## File layout

- `server.py` — FastAPI app + uvicorn launch. Handles frozen mode:
  in PyInstaller bundle, static comes from `sys._MEIPASS`, profiles
  persist to `%APPDATA%\wheelcraft\profiles\`. In source mode, both
  are next to the script.
- `wheelmap/` — internal Python package. Name kept from before the
  rename to "wheelcraft" for the user-facing branding. Renaming the
  package is a low-priority cleanup; not user-visible.
  - `xinput.py` — `ctypes` wrapper around `XInputGetState`, plus
    button-bit constants and the `GamepadState` dataclass.
  - `pipeline.py` — `WheelPipeline`: owns the 200 Hz loop, the active
    `Profile` reference, and the `Snapshot` for the UI. Daemon thread.
  - `transform.py` — pure functions: `apply_profile(GamepadState, Profile)
    -> GamepadState`. Bipolar (steering) and unipolar (pedals) remap.
  - `profile.py` — Pydantic `AxisConfig` and `Profile` schema. `Profile.default()`
    creates an identity-passthrough profile.
  - `store.py` — disk I/O for profiles. Each profile = a JSON file in
    `profiles/`. `_state.json` holds the active profile name (gitignored).
- `static/` — `index.html`, `app.js`, `app.css`. Single page.
- `profiles/` — JSON profile files. Only `default.json` is in git;
  `_state.json` is gitignored runtime state.
- `installer/wheelcraft.iss` — Inno Setup script for the Windows installer.
- `installer/fetch_vendor.bat` — downloads ViGEmBus v1.22.0 for bundling.
- `installer/vendor/` — gitignored; holds the downloaded ViGEmBus.exe.
- `build.bat` — runs PyInstaller. Outputs `dist/wheelcraft/wheelcraft.exe`.
- `run.bat` — dev launcher: auto-creates `.venv` on first run, starts
  `server.py`, opens the browser.
- `release.bat` — `release.bat <version>` does the full release pipeline:
  bumps version, builds, compiles installer, tags, pushes, creates GH release.

## Commands

| Task | Command |
|---|---|
| Run in dev mode | `run.bat` |
| Build standalone exe | `build.bat` → `dist/wheelcraft/wheelcraft.exe` |
| Compile installer | `installer/fetch_vendor.bat` then ISCC on `installer/wheelcraft.iss` |
| Full release | `release.bat 0.x.y` |
| Reinstall deps | `.venv\Scripts\python.exe -m pip install -r requirements.txt` |

## Non-obvious facts (DO NOT LOSE THESE)

1. **Anaconda Python `ffi.dll` quirk.** This machine's base Python is
   Anaconda's `C:\Arvind\Anaconda3`. Its `_ctypes.pyd` imports `ffi.dll`
   (Anaconda's filename), not `libffi-8.dll` (python.org's filename).
   PyInstaller's automatic dependency detection misses it, so `build.bat`
   has a manual `--add-binary "...\Library\bin\ffi.dll;."` to include it.
   Without this fix, the built exe crashes on import with
   `ImportError: DLL load failed while importing _ctypes`. If the user
   ever switches to python.org Python, this workaround can be removed.

2. **Game XInput slot priority.** The user's wheel takes XInput slot 0 (it
   was plugged in first). Our virtual pad goes to slot 1. Most games default
   to slot 0, so games bypass our transformations unless the user manually
   picks "Controller 2" in game settings. HidHide does NOT reliably solve
   this — HidHide hides HID, but games typically use the XInput API which
   talks to `xusb22.sys` directly. To truly hide the wheel from games we'd
   have to `Disable-PnpDevice` (admin) and switch our reader to raw HID.
   Not implemented.

3. **Wheel hardware saturation.** The user has a Nitho-branded DragonRise
   wheel (VID `0079` / PID `189c`) that hardware-saturates LX at ~75%
   physical rotation. There is no software workaround — the wheel firmware
   stops emitting data past that point. The UI rotor angle was tuned
   (`WHEEL_VIS_MAX_DEG = 90` in `static/app.js`) to look less misleading,
   but the lost 25% physical range is gone in-game too.

4. **Center-bias bug fix.** When `output_floor_pct > 0`, the naive remap
   formula gives a non-zero output at exactly wheel-center (`mag = 0`).
   The fix in `transform.py` is `<=` (not `<`) for the inner-deadzone
   check, and `>=` (not `>`) for the outer-saturation check. The JS
   mirrors this in `static/app.js`. Both must stay in sync. Critical for
   correctness — do not "simplify" back to `<` / `>`.

5. **ViGEmBus driver is a hard dependency.** `vgamepad` is a thin wrapper
   around `ViGEmClient.dll`, which talks to the `ViGEmBus` kernel driver
   service. If the service isn't installed, `VX360Gamepad()` raises at
   import time. The installer bundles `ViGEmBus.exe` v1.22.0 and runs it
   silently if `sc query ViGEmBus` returns non-zero.

6. **vgamepad's bundled DLL.** `build.bat` uses `--collect-all vgamepad`
   so PyInstaller bundles `vgamepad/win/vigem/client/{x64,x86}/ViGEmClient.dll`.
   Without this flag the built exe crashes on first virtual-pad creation.

7. **Read path goes through XInput, not pygame.** We initially tried
   `pygame.joystick` for reading the wheel, but SDL's joystick layer
   drops the LX axis and D-pad for this specific DragonRise VID/PID
   (known SDL quirk). The fix was to read XInput directly via `ctypes`.
   See `wheelmap/xinput.py`. Don't reintroduce pygame here.

8. **Live editing flow.** The browser POSTs the full profile JSON to
   `/api/profiles/active` on every slider change (debounced ~40 ms).
   The server hot-swaps the in-memory profile via `pipeline.set_profile()`
   — assignment to `self._profile` is atomic in CPython, so no lock is
   needed for the read in the loop. Saving to disk is a separate explicit
   action (PUT `/api/profiles/{name}`).

## Working in this codebase

- Editing static files: just refresh the browser, the FastAPI static
  mount serves them live.
- Editing Python: stop the server (`Ctrl+C` in the run.bat window),
  restart.
- After a backend change, smoke test:
  1. Wheel input arrives (real LX changes when you turn the wheel)
  2. Virtual LX mirrors / transforms as expected
  3. Curve graph in the editor matches the expected shape
  4. Buttons highlight in both the real and virtual button grids
- Don't add features that weren't asked for. The user is iterative and
  pragmatic; bias toward shipping the smallest change that solves the
  named problem.
