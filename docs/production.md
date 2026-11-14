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

Window size defaults to a phone-like portrait frame for layout checks. Resize is allowed; screens should remain usable.

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

## Testing checklist (device)

- [ ] App installs and opens without crash
- [ ] Welcome → Home navigation works
- [ ] Floating bottom nav switches screens
- [ ] Fonts (Lexend) render (no fallback-only look)
- [ ] Orientation / safe areas look acceptable on the target phone
- [ ] (Phase 1) Camera permission prompt and preview
- [ ] (Phase 1) Gallery pick + corrected image display

## Known issues / notes

- **Buildozer on Windows**: prefer WSL2 or a Linux VM; expect long first builds (NDK/SDK download).
- **Python 3.13**: confirm Kivy wheel availability for your OS; if desktop install fails, use 3.11/3.12 in the venv.
- **Kivy camera on desktop** differs from Android `Camera` / `Camera2` providers — Phase 1 must test live feed on-device.
- **Font packaging**: `assets/fonts/*.ttf` must be listed in Buildozer `source.include_exts` (`.ttf` included in spec).
- Soft shadows are approximated with layered rounded rects; they will not match Material elevation exactly.

## `buildozer.spec` highlights

- `package.name` / `package.domain` set for ColorSight
- Orientation: portrait
- Requirements: `python3,kivy,numpy,opencv` (OpenCV Android recipe may need pinning — verify on first real build)
- Permissions: camera + storage as above
