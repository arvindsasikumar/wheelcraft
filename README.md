# wheelcraft

A Windows tool that reads a racing wheel via XInput, applies per-profile
transformations (deadzones, output floor/ceiling, response curve, button
remap), and emits the result as a virtual Xbox 360 controller via ViGEmBus.
Includes a browser-based live visualizer and profile editor served at
`http://localhost:8765`.

Use it when your wheel has annoying quirks the game can't fix on its own —
e.g. small wheel turns ignored by the game (in-game deadzone), pedals that
need full pressure, paddles you'd like to remap.

---

## Install (recommended, ~30 seconds)

1. Go to the [latest release](https://github.com/arvindsasikumar/wheelcraft/releases/latest).
2. Download **`wheelcraft-setup.exe`** (the file ending in `.exe`).
3. Run it. The installer bundles the ViGEmBus driver and installs it silently
   if it's not already on your system. It also creates a Start Menu entry and
   (optional) Desktop shortcut.
4. Launch **wheelcraft** from the Start Menu or desktop. A browser tab opens
   at `http://localhost:8765` showing the live visualizer + profile editor.

### "Windows protected your PC" warning

The installer isn't signed with a paid code-signing certificate, so on first
download Windows SmartScreen shows a blue "Windows protected your PC" screen.
This is normal for indie / open-source Windows apps. To bypass:

- Click the small **"More info"** link, then **"Run anyway"**.
- *Or* before running: right-click the downloaded file → **Properties** →
  tick **"Unblock"** at the bottom → OK. Then double-click as normal.

### Uninstalling

Start Menu → **wheelcraft** → right-click → **Uninstall**. Your saved
profiles are preserved at `%APPDATA%\wheelcraft\profiles\` and reused if you
reinstall later.

---

## Using it

Once launched, wheelcraft adds a **second** Xbox 360 controller to Windows
(the real wheel is the first). Games read controllers by "slot" and usually
default to slot 1, which is your raw wheel — bypassing your tuning. So:

- In your game's controller settings, **pick "Controller 2"** (or the second
  Xbox controller in the list). That's the tuned virtual pad wheelcraft
  exposes. Once selected, your profile transformations take effect.
- Switching profiles in wheelcraft (top-left dropdown) applies them live —
  no game restart required.

### Quitting

Click the **quit** button at the top of the wheelcraft browser tab. The
server exits cleanly. To restart, launch from the Start Menu shortcut.

### Where things live

- Saved profiles: `%APPDATA%\wheelcraft\profiles\` (one JSON file per profile)
- Diagnostic log: `%APPDATA%\wheelcraft\wheelcraft.log` (if anything crashes)
- Installed app: `C:\Program Files\wheelcraft\`

---

## What the UI looks like

- **Live input panel** — a wheel viz that rotates with yours, pedal bars,
  button grid, and a side-by-side "real → virtual" value table.
- **Per-axis editor** (steering, brake, throttle): friendly-labelled sliders
  for input deadzone, input saturation, output floor (boost small inputs),
  output ceiling (cap max), and sensitivity curve. Live curve preview shows
  the shape and your current input position.
- **Button remap matrix** mapping each physical XInput button to a virtual
  one. Rows highlight when pressed so you can spot which physical control
  fires which slot.
- **Profiles**: dropdown to switch, save / new / delete buttons. Edits
  auto-apply live; explicit "save" persists to disk.

---

## Running from source (developers)

Prerequisites:
- Windows 10 or 11
- Python 3.11 ([python.org](https://www.python.org/downloads/), tick "Add to PATH")
- [ViGEmBus 1.22.0](https://github.com/nefarius/ViGEmBus/releases/download/v1.22.0/ViGEmBus_1.22.0_x64_x86_arm64.exe)
- An XInput-compatible wheel plugged in

Then:

```cmd
git clone https://github.com/arvindsasikumar/wheelcraft.git
cd wheelcraft
run.bat
```

`run.bat` auto-creates a virtualenv on first run, installs deps, then starts
the server and opens the browser.

### Building the installer locally

```cmd
build.bat                         REM PyInstaller bundle in dist\wheelmap\
installer\fetch_vendor.bat        REM downloads ViGEmBus into installer\vendor\
"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" installer\wheelmap.iss
REM Output: installer\Output\wheelcraft-setup.exe
```

### Cutting a release

```cmd
release.bat 0.1.5
```

Bumps version, builds, compiles installer, tags, pushes, creates the GitHub
release with the installer attached.

---

## Architecture

```
real wheel  -> XInputGetState(slot 0)
            -> apply_profile  (deadzones, curves, output floor/ceiling,
                               button remap, invert)
            -> vgamepad.VX360Gamepad.update()   ==  ViGEmBus virtual pad
                                                    (XInput slot 1)
            -> games read the virtual pad
                                  ↓
            -> Snapshot broadcast over WebSocket /live to the browser UI
               at ~60 Hz for visualization
```

The reader/writer loop runs at ~200 Hz in a daemon thread
(`wheelmap/pipeline.py`). The browser UI mirrors the transformation math in
JS for the live curve preview. All persistent state is JSON files in
`%APPDATA%\wheelcraft\` (packaged install) or `./profiles/` (source mode).

See `CLAUDE.md` for non-obvious project facts (Anaconda Python's `ffi.dll`
quirk, XInput slot priority, the `--windowed` PyInstaller `isatty` trap,
etc.) — useful if you're modifying or debugging.
