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

- Live flow: **checklist → Trivector CCT → hue → results** (`colorsight/screens/test_screen.py`).
- First **Start test** builds a `TrivectorSession` (phone mode: 8 reversals/axis); UI shows “Preparing trials…”.
- Headless smoke: `python tools/flow_trivector.py` → prints `FLOW_OK …`.
- Saved profile path (logs/docs only): Kivy `user_data_dir` / `correction_profile.json` — UI shows a friendly confirmation, not the path.
- Progress UI widget is `PillProgressBar` (not Kivy’s `ProgressBar`).
- Arrow pad: D-pad `ArrowKey` widgets with `Icon(..., icon_size=28)` — do not pass `size=dp(28)`.
- Trial shell is persistent (texture blit ~1 ms); stimulus request size 512 for crisp display.
- Trivector gates: `python -m unittest tests.test_trivector -v`
- Legacy plate gates (still required): `python -m unittest tests.test_plate_validation tests.test_plate_recognizability -v`
- Full suite: `python -m unittest discover -s tests`
- Legacy plate previews: `python tools/preview_plates.py` → `debug/plates/` (gitignored).

### Photos / image pipeline

```bash
# Pipeline unit tests (EXIF, resize, RGB/BGR, before/after split)
python -m unittest tests.test_image_pipeline -v

# Headless pipeline smoke (correct + save to Pictures/ColorSight)
python tools/flow_photos.py          # → FLOW_PHOTOS_OK …

# Photos helpers (strength, divider, MAD, comparison, mode save)
python -m unittest tests.test_photos_pipeline -v

# Desktop UI smoke (strength default/reset, modes, divider, save×3, comparison, share)
python tools/smoke_photos_ui.py      # → SMOKE_PHOTOS_OK … profile_strength_ok …
```

If mode taps crash with `NoneType is not callable`, check that Photos widgets do not use `on_mode` / `on_split` as `ObjectProperty` names (see `rules.md`).

- Preview longest side ≈ **1080 px**; full-res only on Save/Share (JPEG quality 95).
- Strength is a **temporary preview override** — does not rewrite `correction_profile.json`.
- UI never shows filesystem paths (pick/save/share confirmations are friendly copy only).

### Android share (FileProvider)

Share uses `Intent.ACTION_SEND` + `FileProvider` URI (`photo_io._share_android`). Packaging needs:

| Piece | Location |
|-------|----------|
| Paths XML | `assets/android/file_paths.xml` → `@xml/file_paths` (`android.add_resources` in `buildozer.spec`) |
| Manifest `<provider>` | Merge `assets/android/fileprovider_snippet.xml` into `<application>` (authority `${applicationId}.fileprovider`) |
| Maven | `androidx.core:core` (listed in `buildozer.spec`) |

Desktop Share falls back to saving into `Pictures/ColorSight/` and showing “Saved to your gallery”.

### Camera / Lens

```bash
python -m unittest tests.test_camera_pipeline -v
# Fake-frame UI smoke (no webcam required)
set COLORSIGHT_FAKE_CAMERA=1   # PowerShell: $env:COLORSIGHT_FAKE_CAMERA=1
python tools/smoke_camera_ui.py   # → SMOKE_CAMERA_OK …
# Real webcam (desktop)
python main.py   # open Camera; Settings → Show camera FPS
```

| Topic | Notes |
|-------|--------|
| Desktop | OpenCV `VideoCapture(0)`; falls back to synthetic frames if open fails |
| Android | Runtime `CAMERA` via `request_camera_permission`; denied → rationale card + “Open settings”. Prefer Camera4Kivy (`camera4kivy` in `buildozer.spec`) |
| Pipeline | Latest-frame drop; live longest ≈ **560 px**; bg process + blit; start on enter / stop on leave; pause/resume |
| Capture | Saves current mode to ColorSight album (MediaStore / Pictures) — no paths in UI |
| Lens | Nav item opens Camera with loupe on (shared widgets) |

#### Measured FPS (desktop smoke / fake source)

| Setup | Approx. processed FPS |
|-------|------------------------|
| FakeFrameSource @ 20 Hz, Corrected mode, 390×844 window (Intel UHD 620) | **~15–20** (poll 20 Hz; drops if still processing) |
| Mid-range phone target | **15+** with live longest ≤560; enable Settings → Show camera FPS on device to record |

Known limits: first OpenCV open can lag; Android Camera4Kivy preview wiring may need a device pass to attach the Preview widget callback into `AndroidCameraSource.push_frame_rgb`. Heavy Simulation + loupe on low-end devices may dip below 15 fps — drop frames rather than queue.

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
| `CAMERA` | Live Camera / Lens — request at runtime with rationale + settings fallback |
| `READ_MEDIA_IMAGES` (API 33+) | Fallback gallery access on older flows |
| `READ_EXTERNAL_STORAGE` | Pre-13 gallery fallback |
| `WRITE_EXTERNAL_STORAGE` | Legacy pre-10 only; **not** required for MediaStore saves on Android 10+ |
| `INTERNET` | Optional; keep off unless a feature needs it |

### Photos pick & save (Android)

| API | Pick | Save |
|-----|------|------|
| **13+ (API 33+)** | System **Photo Picker** (`android.provider.action.PICK_IMAGES`) via pyjnius — **no** broad storage permission | `MediaStore` insert with `RELATIVE_PATH=Pictures/ColorSight` (scoped storage) |
| **10–12** | `ACTION_GET_CONTENT` / openable URI → copy to app temp | Same MediaStore path; no `WRITE_EXTERNAL_STORAGE` needed |
| **≤9** | May need `READ_EXTERNAL_STORAGE` runtime grant (`ensure_read_images_permission`) | MediaStore or app `getExternalFilesDir` fallback |

Desktop: tkinter file chooser; save under `~/Pictures/ColorSight/`.

`pyjnius` + `android` are already in `buildozer.spec` requirements for these bridges.

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
- [ ] Vision Test completes (checklist → Trivector → hue → results) and Save profile writes JSON
- [ ] Result disclaimer visible (screening ≠ diagnosis; screens vary)
- [ ] Photos: no-profile CTA; with profile → Corrected @ 0% divider; Strength matches saved %; Save/Share
- [ ] Photos on Android 13+: Photo Picker works without granting all-files storage
- [ ] Camera: permission rationale / deny → Open settings; live Corrected when profile exists
- [ ] Camera: freeze/capture → ColorSight album; loupe names colors; Lens nav enables loupe
- [ ] Settings: Show camera FPS toggles overlay; note measured fps on device

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
