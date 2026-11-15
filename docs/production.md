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

Desktop (`main.py`): Config graphics default **390×844** (resizable) **only when not android/ios**. For phone-density checks use `python tools/run_phone_sim.py` (540×1200 @ density 1.375).

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
- Arrow pad: **inverted-T** `ArrowKey` widgets (72 dp, 8 dp gaps) with `Icon(..., icon_size=28)` — do not pass `size=dp(28)`. Desktop physical arrow keys answer trials.
- Trial shell is persistent (texture blit ~1 ms); stimulus request size 512; display ~132 dp; fits 360×640 without scroll.
- Home chips: auto-width + horizontal scroll (`tools/smoke_ui_polish.py`, `tools/smoke_ui_flow.py`).
- Headers: `ScreenHeader` with `header_gap` / `screen_top` on Test, Photos, Camera, Settings, Profile.
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

## Cloud build (GitHub Actions) — preferred

Build the debug APK in the cloud so you do **not** need a local Buildozer/WSL toolchain.

### Run the workflow

1. Push this repo to GitHub (private is fine) under **ahmadsaeedmirza**.
2. Open **Actions → Android APK**.
3. Either:
   - **Run workflow** (`workflow_dispatch`), or
   - Push any commit to a branch named **`build-apk`**.
4. Wait for the job (first run can take **1–3+ hours**; later runs reuse `~/.buildozer` + `./.buildozer` cache).

Workflow file: `.github/workflows/android.yml` (ubuntu-22.04, Java 17, `cython==0.29.36`, `buildozer -v android debug`, timeout 360 min).

### Download the APK

On a **successful** run: open the workflow run → **Artifacts** → download **`colorsight-apk`** (contains `bin/*.apk`, arm64-v8a debug).

**Uninstall the previous debug build first.** Each cloud run signs with a **new debug keystore**, so `adb install -r` often fails with a signature mismatch. Remove the old app, then install:

```bash
adb uninstall org.colorsight.colorsight
adb install colorsight-*-arm64-v8a-debug.apk
```

**Play Protect** may warn that the app was “built for an older version of Android” or is unrecognized — expected for **debug** APKs (and until `android.api` tracks current Play targets). Tap *More details → Install anyway* (or equivalent). Release builds with a proper target SDK + upload key are a later step.

### Desktop phone-density layout check

Before building, catch scaling/clipping bugs:

```bash
python tools/run_phone_sim.py
# Automated pass over Welcome/Home/Test/Photos/Camera/Profile/Settings:
python tools/smoke_phone_sim.py   # → SMOKE_PHONE_SIM …
```

Sim: **540×1200** window at **`KIVY_METRICS_DENSITY=1.375`** (half-scale of 1080×2400 @ density 2.75). `main.py` only sets the 390×844 desktop window when `platform` is not android/ios — never touch `Window.size` on device.

### If the build fails

1. Open the failed run → **Artifacts** → download **`colorsight-build-failure-log`** (last **1500** lines) and/or **`colorsight-build-full-log`** (full `buildozer-ci.log`, 3-day retention).
2. Match the error to the troubleshooting table below (FreeType, NDK, `PIP_CONSTRAINT` / charset-normalizer, pins).
3. Fix `constraints.txt` / `buildozer.spec` / workflow as needed, push, and re-run (cache makes reruns faster).

### Known cloud / Buildozer pitfalls

| Pitfall | What we do |
|---------|------------|
| FreeType download blocked (Savannah) | Manual SourceForge `.tar.gz` + `.mark-…` (see troubleshooting) — rare on GitHub runners; more common on restricted networks |
| NDK 25b / NumPy `unordered_map` | Use **`android.ndk = 28c`** |
| `charset-normalizer` android wheel on host pip | p4a **drops** `requirements=` pins for pure-Python pip modules, so a `buildozer.spec` pin is ignored. Use repo-root **`constraints.txt`** (`charset-normalizer==3.4.9`) and set **`PIP_CONSTRAINT`** on the Buildozer step (see workflow) so every pip call — including the dry-run resolver — honors it |
| Corrupt Buildozer / p4a venv | Delete the bad env under `.buildozer/` (or clear the Actions cache for `buildozer-*`) and rebuild clean |
| Old kivy/numpy/pillow pins on Python 3.14 | Keep those **unpinned**; single `version = 0.1.0` (no `version.regex`) |
| **UI stuck in a ~390 px box (bottom-left) on phone** | Desktop `Window.size` / Config **390×844** was also applied on Android. Guard with `platform not in ('android','ios')` in `main.py`; never set window size in `app.py` on device. Use `tools/run_phone_sim.py` to catch this |
| **Black flash between screens** | Every `Screen` + root must paint an opaque themed (or neutral) bg in `canvas.before`; keep `Window.clearcolor` in sync with the theme |
| **On-device debugging** | Settings → Debug → **View recent log** (last 300 lines, copy). Log file rotates under `user_data_dir` (paths never shown in UI) |
| Play Protect / “older Android” on install | Normal for **debug** APKs; install anyway. Target SDK is `android.api = 35` (min 24) |
| `INSTALL_FAILED_UPDATE_INCOMPATIBLE` | New debug key each CI run — **uninstall** `org.colorsight.colorsight` before installing |

Local WSL steps below remain as a **fallback** if Actions is unavailable.

## Android packaging (Buildozer) — WSL2 fallback (Ubuntu) from Windows

Native Windows Buildozer is **not** recommended. Prefer the **Cloud build** above; use **WSL2 + Ubuntu** only as a fallback.

### 1. Install WSL2 (Windows PowerShell as Administrator)

```powershell
wsl --install -d Ubuntu
# Reboot if prompted, then open Ubuntu from the Start menu
```

### 2. One-time Ubuntu packages

```bash
sudo apt update
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip python3-venv \
  autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev \
  libtinfo5 cmake libffi-dev libssl-dev
pip3 install --user buildozer cython
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
buildozer --version
```

### 3. Get the project into WSL

**Option A — mount your Windows drive (simplest while developing on Windows):**

```bash
cd "/mnt/d/University/6th Semester/Digital Image Processing/Sem Project/ColorSight"
# Adjust the path if your repo lives elsewhere under /mnt/c/... or /mnt/d/...
```

**Option B — copy into the Linux home (often faster builds):**

```bash
cp -a "/mnt/d/University/6th Semester/Digital Image Processing/Sem Project/ColorSight" ~/ColorSight
cd ~/ColorSight
```

### 4. Build the debug APK

```bash
chmod +x tools/build_android.sh
./tools/build_android.sh
# Equivalent: buildozer android debug && cp -f bin/colorsight-*-debug.apk dist/
```

First run downloads the Android SDK/NDK — expect **30–90+ minutes**. Later builds are much faster. Output APK:

- `bin/colorsight-<version>-arm64-v8a-debug.apk` (64-bit only)
- Copied to `dist/` by the script

### 5. USB debugging + install with adb

On the phone:

1. **Settings → About phone** → tap **Build number** 7 times → Developer options.
2. Enable **USB debugging** (and “Install via USB” if present).
3. Connect USB; accept the RSA prompt on the phone.

From **Windows** (with [platform-tools](https://developer.android.com/tools/releases/platform-tools) on PATH) or from WSL (if `adb` sees the device):

```bash
adb devices
adb install -r dist/colorsight-*-debug.apk
```

Launch **ColorSight** from the app drawer.

### 6. Release build (later)

```bash
buildozer android release
```

Sign with a proper keystore before Play Store distribution (not configured yet).

### FileProvider / packaging checklist

| Item | Wired how |
|------|-----------|
| `file_paths.xml` | `android.add_resources` → `@xml/file_paths` |
| Manifest `<provider>` | Merge `assets/android/fileprovider_snippet.xml` into the generated manifest if share fails (p4a may not auto-merge; verify on device) |
| `core/*`, `colorsight/*`, `assets/**` | `source.include_patterns` |
| Icon / splash | `assets/icon.png`, `presplash.png`, adaptive foreground/background |
| Portrait + api 33 / min 24 / **arm64-v8a only** + NDK **28c** | `buildozer.spec` (64-bit APK; covers almost all current phones) |

### Troubleshooting (typical failures)

| Symptom | What to try |
|---------|-------------|
| **download.savannah.gnu.org unreachable (FreeType)** | p4a cannot fetch FreeType from Savannah. Manual workaround: download `freetype-2.14.1.tar.xz` from [downloads.sourceforge.net/freetype/freetype2/2.14.1/](https://downloads.sourceforge.net/freetype/freetype2/2.14.1/); convert it to `.tar.gz`; place it in `.buildozer/android/platform/build-arm64-v8a/packages/freetype/` (or `build-arm64-v8a_armeabi-v7a/…` if you still have a dual-arch tree); then `touch .mark-freetype-2.14.1.tar.gz` in that same folder and rebuild |
| **Version pins break the build on new p4a** | python-for-android **2026.05.09** defaults to **Python 3.14**. Old pins (`kivy==2.3.0`, `numpy==1.26.4`, `pillow==10.4.0`) fail on 3.14; the numpy pin also fails because the recipe looks for git tag `1.26.4` while the tag is `v1.26.4`. Fix: leave those unpinned in `buildozer.spec` (desktop `requirements.txt` alone). Clean `.buildozer` if a failed pin left a bad cache |
| **NumPy fails with `no template named unordered_map`** | NDK **25b** libc++ is too old for NumPy 2.3 (`unique.cpp` missing an include). Use **`android.ndk = 28c`** (what p4a 2026.05.09 recommends). Clean the NDK/build cache and rebuild |
| **`charset-normalizer` / “is not a supported wheel on this platform”** | p4a resolves pure-Python helpers with `pip … --dry-run --platform=android_24_arm64_v8a` and **ignores** `buildozer.spec` version pins for those modules, so it picks **3.5.2**’s android wheel that host pip cannot install. Fix: `constraints.txt` with `charset-normalizer==3.4.9` + workflow env **`PIP_CONSTRAINT=${{ github.workspace }}/constraints.txt`** (do not put the pin back in `requirements`) |
| OpenCV recipe fails | Keep unpinned `opencv` in requirements; clean `.buildozer` and rebuild; ensure NDK **28c** matches `android.ndk` |
| NDK/SDK download stuck | Check disk space (~20+ GB); retry; set `ANDROIDSDK` / `ANDROIDNDK` if you already have them |
| Cython / Kivy mismatch | Prefer unpinned `kivy` (recipe picks a 3.14-compatible build); `pip3 install --user 'cython<3'` only if an older recipe still needs it |
| Camera4Kivy missing classes | Confirm `camera4kivy` in requirements; add/update gradle deps per Camera4Kivy docs; clean build |
| Permission denied at runtime | CAMERA / READ_MEDIA_IMAGES declared; app requests CAMERA at runtime — use Settings → Open settings card if denied |
| Share crashes | Ensure FileProvider authority `${applicationId}.fileprovider` and `@xml/file_paths` are in the final APK manifest |
| `buildozer` not found | `pip3 install --user buildozer` and ensure `~/.local/bin` is on `PATH` |
| Corrupt / half-built p4a venv | Delete `.buildozer/android/platform/build-*/build/venv` (or the whole `.buildozer` tree) and rebuild; on Actions, clear the `buildozer-*` cache then re-run |

**NumPy on Android vs desktop:** p4a’s default numpy is **2.x**, which may differ from an older desktop pin. After bumping Android recipes, run `python -m unittest discover -s tests` against the latest numpy on desktop to confirm `/core` still passes (result logged in `memory.md`).

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

**Verified on desktop (this repo):** unit suite, trivector/photos/camera smokes, Welcome/Home/Profile/Settings UI logic.

**Not verified without a real device / APK build** — please run these yourself:

- [ ] APK installs (`adb install`) and opens without crash
- [ ] First launch → Welcome → color test; later launch → Home
- [ ] Android back button returns to Home from feature screens
- [ ] Floating nav + safe areas on a notched phone; nothing under the nav
- [ ] Vision Test → Save profile; Profile shows type / severity / date / axes
- [ ] Photos: Android 13+ Photo Picker (no all-files grant); Corrected @ 0% divider; Save + Share sheet
- [ ] MediaStore album **ColorSight** appears in Gallery
- [ ] FileProvider share to WhatsApp / Files works
- [ ] Camera: permission deny → Open settings; live Corrected; freeze/capture; FPS overlay
- [ ] Lens nav enables loupe; `name_color` stable
- [ ] Record on-device FPS (Settings → Show camera FPS) and note mid-range phone numbers

## Known issues / notes

- **Buildozer on Windows**: use WSL2 (above); expect long first builds.
- **p4a 2026.05.09**: defaults to Python 3.14; keep recipe deps unpinned; constrain charset-normalizer via **`PIP_CONSTRAINT` / `constraints.txt`**; use NDK **28c** and **arm64-v8a only** (see troubleshooting).
- **APK is 64-bit only** (`arm64-v8a`) — covers almost all current phones; no `armeabi-v7a` slice.
- **Python 3.13 desktop**: if Kivy wheels fail, use 3.11/3.12 in the venv.
- **Camera4Kivy**: desktop uses OpenCV; Android Preview widget callback may need a device pass to fully wire `AndroidCameraSource.push_frame_rgb`.
- **FileProvider**: resources are packaged; if share fails, manually merge `fileprovider_snippet.xml`.
- **Radius 999**: always clamp (see `design.md`).
- Soft shadows are layered rounded rects, not Material elevation.

## `buildozer.spec` highlights

- Title **ColorSight**; `org.colorsight.colorsight`; single **`version = 0.1.0`** (no `version.regex` / `version.filename`)
- Portrait; **`android.api = 35`** / min 24; **`android.archs = arm64-v8a`** (64-bit only); **`android.ndk = 28c`**
- Requirements: `python3,kivy,numpy,opencv,pillow,pyjnius,android,camera4kivy` — do not re-add old kivy/numpy/pillow `==` pins; charset-normalizer via `constraints.txt` + `PIP_CONSTRAINT` in CI
- CAMERA + READ_MEDIA_IMAGES (+ legacy storage); FileProvider via `android.add_resources`; icon / adaptive / cream splash
- Cloud CI: `.github/workflows/android.yml` (manual + `build-apk` branch); failure artifacts: last 1500 lines + full log (3-day retention)
