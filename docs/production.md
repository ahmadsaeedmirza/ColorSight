# Production — Build & device testing

## Desktop run (primary during Phase 0)

```bash
# From project root
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
python main.py
```

Window size defaults to a phone-like portrait frame for layout checks (OS DPI may scale the actual pixel size). Resize is allowed; screens should remain usable.

### Core engine unit tests

```bash
# From project root (venv active)
python -m unittest discover -s tests -v
```

Requires NumPy + OpenCV (`opencv-python` or `opencv-python-headless`).

### Vision Test notes (desktop)

- First **Start test** generates 14 procedural plates (~1–3 s on a laptop); UI shows “Preparing plates…”.
- Saved profile path: Kivy `user_data_dir` / `correction_profile.json` (see `colorsight.storage.profile_path`).
- Plate artwork is original/procedural — do not replace with copyrighted Ishihara scans.

## Android packaging (Buildozer)

Buildozer is typically run on **Linux** (or WSL2 / a CI Linux image). Native Windows Buildozer is not recommended.

### One-time host setup (Linux / WSL)

```bash
sudo apt update
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool
sudo apt install -y libffi-dev libssl-dev
pip3 install --user buildozer cython
```

Ensure Android SDK/NDK are available (Buildozer can download them on first run).

### Build debug APK

```bash
cd /path/to/ColorSight
buildozer android debug
```

APK output (typical):

`bin/colorsight-*-debug.apk`

### Install on a real device

1. Enable **Developer options** → **USB debugging** on the phone.
2. Connect via USB (or use wireless ADB).
3. Install:

```bash
adb install -r bin/colorsight-*-debug.apk
```

4. Launch **ColorSight** from the app drawer.

### Release build (later)

```bash
buildozer android release
```

Sign with a proper keystore before Play Store distribution (not configured in Phase 0).

## Permissions

Declared in `buildozer.spec` / AndroidManifest (via Buildozer):

| Permission | Why |
|------------|-----|
| `CAMERA` | Live camera correction + magnifier (Phase 1) |
| `READ_EXTERNAL_STORAGE` / media read | Pick photos to correct (Phase 1) |
| `WRITE_EXTERNAL_STORAGE` (older APIs) | Save corrected images if needed |
| `INTERNET` | Optional; keep off unless a feature needs it |

Phase 0 shell does not request runtime camera/storage usage yet; declare early so packaging is ready.

## Asset packaging (fonts & icons)

Must ship with the APK:

| Path | License | Notes |
|------|---------|-------|
| `assets/fonts/Lexend-*.ttf` | OFL (`assets/fonts/OFL.txt`) | UI typeface |
| `assets/icons/MaterialIcons-Regular.ttf` | Apache 2.0 (`assets/icons/LICENSE.txt`) | Ligature icons |

`buildozer.spec`:

- `source.include_exts` includes `ttf`, `otf`, `txt`, `md`, `py`
- `source.include_patterns` includes `assets/*`, `assets/fonts/*`, `assets/icons/*`, `core/*`, `colorsight/*`

## Testing checklist (device)

- [ ] App installs and opens without crash
- [ ] Welcome → Home navigation works
- [ ] Floating bottom nav fits width (side margins), switches screens, FAB raised and tappable
- [ ] Lexend fonts + Material Icons render (no empty boxes)
- [ ] Selected chips show white text on dark pills
- [ ] Home / placeholder content scrolls clear of the nav bar
- [ ] Orientation / safe areas look acceptable on the target phone
- [ ] Vision Test completes (plates → hue → results) and Save profile writes JSON
- [ ] Result disclaimer visible (screening ≠ diagnosis; screens vary)
- [ ] (Phase 1) Camera permission prompt and preview
- [ ] (Phase 1) Gallery pick + corrected image display

## Known issues / notes

- **Buildozer on Windows**: prefer WSL2 or a Linux VM; expect long first builds (NDK/SDK download).
- **Python 3.13**: confirm Kivy wheel availability for your OS; if desktop install fails, use 3.11/3.12 in the venv.
- **Kivy camera on desktop** differs from Android `Camera` / `Camera2` providers — Phase 1 must test live feed on-device.
- **Radius 999**: never pass unclamped into `RoundedRectangle` — use `clamp_radius` (see `design.md`).
- Soft shadows are approximated with layered rounded rects; they will not match Material elevation exactly.
- **`core/` packaging**: Android builds must include `core/*` (color engine) alongside `colorsight/*`.

## `buildozer.spec` highlights

- `package.name` / `package.domain` set for ColorSight
- Orientation: portrait
- Requirements: `python3,kivy,numpy,opencv` (OpenCV Android recipe may need pinning — verify on first real build)
- Permissions: camera + storage as above
- Icons + fonts via `assets/**`; engine via `core/*`
