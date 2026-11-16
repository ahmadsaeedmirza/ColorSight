# Production — Build & device testing

## If you see “ColorSight could not start”

The app hit a fatal startup error and showed the plain fallback screen (white background, black text).

1. Tap **Copy details**.
2. Paste into a message / issue (includes exception type + last log lines).
3. Optional: **Reset app data** clears prefs/theme only (keeps your vision-test profile), then **Try again**.
4. Startup breadcrumbs in Settings → Debug → View recent log look like `startup:stage +Nms total=…`.

## If you see splash then a black / empty screen

That usually meant the splash was dismissed while the UI was still importing heavy modules (OpenCV / Camera) on a dark clearcolor, or the current screen stayed stuck at the default **100×100** size. Current builds: cream clearcolor + Android loading screen until the first real frame; essential screens (Welcome/Home) paint first; deferred screens load right after; layout watchdog trips if the current screen is tiny vs the window. If it still happens, grab `adb logcat` around `startup:` lines and Settings → Debug → View recent log after a force-stop.

## Before you push (Android / cloud build)

Run these **before** pushing to `build-apk` or triggering **Android APK**:

```bash
# From project root (venv active)
python tools/preflight.py
# CI-like (skip importing GUI modules):
COLORSIGHT_SKIP_GUI=1 python tools/run_unit_tests.py
# Full suite including GUI tests (needs a display / Kivy Window):
python tools/run_unit_tests.py
# python -m unittest discover -s tests -v
```

**CI headless testing:** the GHA `preflight` job installs `xvfb` + SDL/GL libs, pip-installs `numpy` / `pillow` / **`opencv-python-headless`** / `kivy` (core tests import `cv2`), and runs:

```bash
COLORSIGHT_SKIP_GUI=1 COLORSIGHT_HEADLESS=1 \
  xvfb-run -a -s "-screen 0 1280x800x24" python tools/run_unit_tests.py
```

`COLORSIGHT_SKIP_GUI=1` skips importing GUI modules on CI (lens/chip/theme). Those GUI tests still exist and run locally; they call `tests.gui_guard.ensure_kivy_window` and **SkipTest** if Window/OpenGL is unavailable — never abort with X-server exit 102. Desktop smoke / phone-sim stay **local-only** (`tools/smoke_*.py`, `tools/run_phone_sim.py`).

On **WSL/Linux** you can mirror CI with the same `xvfb-run` line. On **Windows**, run `python tools/preflight.py` + unit tests with a real desktop session (or `COLORSIGHT_SKIP_GUI=1`).

Then push / dispatch the workflow. Mistakes that used to cost a 30–90 minute Buildozer run now fail in the **`preflight`** job (~2 minutes).

### Avoided pitfalls (why preflight exists)

| Pitfall | What goes wrong | Guard |
|---------|-----------------|-------|
| Duplicate `version` / `version.regex` + `version.filename` | Buildozer “version defined in two places” | preflight: exactly one `version =` |
| Pinned `requirements=` (`kivy==…`) | p4a / Python 3.14 resolve failures | preflight: no `==` in requirements |
| Missing `charset-normalizer` constraint | Host pip grabs `android_*` wheel → install fail | `constraints.txt` + `PIP_CONSTRAINT`; preflight checks file |
| Stale `.buildozer/.../build/venv` | `ImportError: capture_logging` | CI + `build_android.sh` delete venv; never cache it |
| Wrong NDK / arch | NumPy / CameraX break | `android.ndk=28c`, `android.archs=arm64-v8a` only |
| CRLF in `.py` / `.sh` / `.yml` / `.spec` | Hooks / shell / p4a misparse | `.gitattributes` + preflight CRLF scan |
| `echo \| grep` under `pipefail` | False packaging-check failure | File-based greps only |
| Custom widget named like a Kivy builtin / `size=dp(n)` / `on_*` props | Runtime crash on device | preflight Kivy pitfalls |

Local WSL builds also run preflight via `tools/build_android.sh`.

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

Share uses `Intent.ACTION_SEND` + `FileProvider` URI (`photo_io._share_android`) with `FLAG_GRANT_READ_URI_PERMISSION`. Packaging:

| Piece | Location |
|-------|----------|
| Paths XML | `assets/android/file_paths.xml` → `@xml/file_paths` via `android.add_resources` |
| Manifest `<provider>` | `p4a.hook` = `assets/android/p4a_fileprovider_hook.py` injects authority `org.colorsight.colorsight.fileprovider` before Gradle (reliable). Optional `android.extra_manifest_application_xml` = `fileprovider_snippet.xml` if the buildozer key is supported. |
| AndroidX | `android.enable_androidx = True` + `android.gradle_dependencies = androidx.core:core:1.12.0` |
| CI gate | After build, workflow unzips/dumps the APK manifest and **fails** if `fileprovider` is missing |

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
| Desktop | OpenCV `VideoCapture(0)`; if open fails → synthetic **Test pattern** (labeled) only |
| Android | Camera4Kivy + `camerax_provider` CameraX; runtime `CAMERA`; denied / no camera / start fail → error card with **Retry** + **Open settings** (never silent fake) |
| Pipeline | Analyze ~640 long side → latest-frame-wins; live longest **640**; **GPU `mat3`** on reused RGBA texture (no per-frame NumPy color); Strength/mode = uniform only; loupe name ~5 Hz; `connect_camera` / `disconnect_camera` on enter/leave/pause |
| Capture | Current mode → SharedStorage/MediaStore album **ColorSight** — no paths in UI |
| Lens | Nav → Camera + loupe via `Clock.schedule_once` (not mid-transition `sm.current`); Lens nav highlighted while loupe on |
| Packaging | `p4a.hook` = `assets/android/p4a_hook.py`; requirements include `camera4kivy,gestures4kivy,androidstorage4kivy` (pure-Python) |

#### Measured FPS / timing

Target: **≥24 fps**, **&lt;16 ms** Python work/frame on a mid-range phone. Debug line shows `fps · r/u/d ms` (receive / upload / draw); log writes averages every 5 s (`camera_timing …`).

| Setup | Approx. FPS | Notes |
|-------|-------------|--------|
| FakeFrameSource, Corrected, 390×844 (desktop smoke) | **~24–30** | GPU path; poll 30 Hz; latest-frame-wins |
| Mid-range phone (on-device) | _Fill after install: Settings → Show camera FPS → note `N fps · r…/u…/d… ms` here_ | Aim ≥24 fps, python_ms &lt;16 |

Enable **Settings → Show camera FPS** on device. If a phone still stutters, drop `LIVE_LONGEST` to **480** and re-measure.

### Camera / Lens device checklist

1. Uninstall old APK, install fresh build; open Camera (and Lens from nav).
2. Grant CAMERA when prompted — live preview (not color bars). Deny once → card “Camera permission denied” → Open settings / Retry.
3. Flip camera (front mirrored, back upright). Freeze / Capture → “Saved to your gallery” → Gallery album **ColorSight**.
4. Lens: nav stays on Camera with loupe; names colors from the **original** frame (~5 Hz); Corrected still via GPU matrix on the stage. Home → Lens → Camera → Lens → Back must not crash.
5. Photos: **Choose a photo** shows “Opening gallery…”; Settings → Debug → **Test photo picker** logs result. Save → “Saved to your gallery”.
6. Background the app → resume → preview restarts. If anything fails: **Settings → Debug → View recent log** (`photos:` / `camera_event` / `camera_timing` / `uncaught exception` lines).

## Cloud build (GitHub Actions) — preferred

Build the debug APK in the cloud so you do **not** need a local Buildozer/WSL toolchain.

### Run the workflow

1. Run **`python tools/preflight.py`** locally (see **Before you push** above).
2. Push this repo to GitHub (private is fine) under **ahmadsaeedmirza**.
3. Open **Actions → Android APK**.
4. Either:
   - **Run workflow** (`workflow_dispatch`; optional **`clean_cache`** to skip cache restore), or
   - Push any commit to a branch named **`build-apk`**.
5. **`preflight`** job (Python 3.11, ~2 min) installs xvfb/SDL/GL, runs `tools/preflight.py` (no Window), then unit tests under `xvfb-run` with `COLORSIGHT_HEADLESS=1`. **`build`** only starts if preflight passes (`needs: preflight`).
6. Build can take **1–3+ hours** cold; later runs reuse `~/.buildozer` + `./.buildozer` under cache key **`buildozer-v2-<hash of buildozer.spec + constraints.txt + camerax_provider/**>`**, excluding `build/venv`. Concurrency cancels an older run on the same branch.

Workflow file: `.github/workflows/android.yml` (ubuntu-22.04, Java 17, Node-24 action majors, `cython==0.29.36`, `buildozer -v android debug`, timeout 360 min). Before each build the job deletes `build/venv` so p4a cannot corrupt pip. The APK + build logs upload with **`if: always()`** when present. Packaging checks write dumps to files then grep those files (never `echo | grep` under `pipefail`). Job summary (`GITHUB_STEP_SUMMARY`) lists APK name/size, api/ndk/arch, and FileProvider / CAMERA / CameraX results.

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
# Automated pass over Welcome/Home/Test/Photos/Camera/Profile/Settings (+ theme flip):
python tools/smoke_phone_sim.py   # → SMOKE_PHONE_SIM … insets:top=28:bottom=24
```

Sim: **540×1200** at **`KIVY_METRICS_DENSITY=1.375`**, with debug insets **`COLORSIGHT_INSET_TOP=28`** / **`COLORSIGHT_INSET_BOTTOM=24`** (edge-to-edge status + gesture bar). Theme switches rebuild the whole UI. `main.py` only sets the 390×844 desktop window off-device.

### If the build fails

1. If **preflight** failed: read the job log (seconds, not hours) — fix `buildozer.spec` / CRLF / assets / unit tests, then re-run.
2. If **build** failed: **Artifacts** → **`colorsight-build-logs`** (tail + full `buildozer-ci.log`, always uploaded when present).
3. Match the error to the troubleshooting table below (FreeType, NDK, `PIP_CONSTRAINT` / charset-normalizer, pins).
4. Fix `constraints.txt` / `buildozer.spec` / workflow as needed, push, and re-run (`clean_cache` if the cache itself is poisoned).

### Known cloud / Buildozer pitfalls

| Pitfall | What we do |
|---------|------------|
| FreeType download blocked (Savannah) | Manual SourceForge `.tar.gz` + `.mark-…` (see troubleshooting) — rare on GitHub runners; more common on restricted networks |
| NDK 25b / NumPy `unordered_map` | Use **`android.ndk = 28c`** |
| `charset-normalizer` android wheel on host pip | p4a **drops** `requirements=` pins for pure-Python pip modules, so a `buildozer.spec` pin is ignored. Use repo-root **`constraints.txt`** (`charset-normalizer==3.4.9`) and set **`PIP_CONSTRAINT`** on the Buildozer step (see workflow) so every pip call — including the dry-run resolver — honors it |
| **p4a `build/venv` + `capture_logging` ImportError** | p4a re-creates `build/venv` with `python -m venv` **on top of an existing one**, which mixes pip versions (`ImportError: cannot import name 'capture_logging'`). **Always** `rm -rf .buildozer/android/platform/build-*/build/venv` before a build (workflow + `tools/build_android.sh` do this). **Never cache** that venv (Actions cache uses `buildozer-v2-` + path exclusion). Keep `other_builds` / `python-installs` so rebuilds stay fast. |
| **CI packaging check false fail (`pipefail` + Broken pipe)** | Under `set -euo pipefail`, `echo "$BIG" \| grep …` (or `\| head`) can exit non-zero when grep/head closes early → Broken pipe → `! pipeline` looks like a missing CameraX/FileProvider hit even when the APK is fine. **Fix:** write dumps to files (`apk_manifest_dump.txt`, `apk_dex_strings.txt`) and `grep -qiE pattern file` with no pipes; use `\|\| true` on display `head`/`tee` pipes. |
| **RECORD_AUDIO in manifest** | camerax_provider’s hook adds it for video+audio; ColorSight never records. `p4a_hook.py` strips `RECORD_AUDIO` from the generated `AndroidManifest.xml` after inject. |
| Corrupt Buildozer / p4a tree | If wiping only `build/venv` is not enough, delete more of `.buildozer/` or clear the Actions `buildozer-v2-*` cache and rebuild |
| Old kivy/numpy/pillow pins on Python 3.14 | Keep those **unpinned**; single `version = 0.1.0` (no `version.regex`) |
| **UI stuck in a ~390 px box (bottom-left) on phone** | Desktop `Window.size` / Config **390×844** was also applied on Android. Guard with `platform not in ('android','ios')` in `main.py`; never set window size in `app.py` on device. Use `tools/run_phone_sim.py` to catch this |
| **Black flash between screens** | Every `Screen` + root must paint an opaque themed (or neutral) bg in `canvas.before`; keep `Window.clearcolor` in sync with the theme |
| **Theme only half-applies** | Partial `apply_theme` walks leave stale canvas colors. Fix: full `rebuild_ui()` after token update (see `design.md`) |
| **Chrome under status bar (api 35)** | Edge-to-edge: use `Spacing.safe_top` / `safe_bottom` from `safe_area`; verify with phone-sim inset env vars |
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
| `file_paths.xml` | `android.add_resources` → `@xml/file_paths` (+ hook fallback copy) |
| Manifest `<provider>` | `p4a.hook` (`p4a_fileprovider_hook.py`) + optional `android.extra_manifest_application_xml` |
| AndroidX FileProvider class | `android.enable_androidx` + `androidx.core:core` gradle dep |
| CI verify | `.github/workflows/android.yml` → “Verify FileProvider in APK manifest” |
| `core/*`, `colorsight/*`, `assets/**` | `source.include_patterns` |
| Icon / splash | `assets/icon.png`, `presplash.png`, adaptive foreground/background |
| Portrait + api **35** / min 24 / **arm64-v8a only** + NDK **28c** | `buildozer.spec` |

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
| Camera4Kivy / CameraX missing | Ensure `./camerax_provider` is vendored; `p4a.hook` = `assets/android/p4a_hook.py`; `gestures4kivy` + `camera4kivy` in requirements; `android.enable_androidx = True`; CI must pass CameraX/CAMERA checks |
| Color-bar “camera” on phone | Old silent FakeFrameSource fallback — fixed; if seen again, rebuild with CameraX provider and check log for `camera_event` |
| Permission denied at runtime | CAMERA declared; request at runtime — use error card **Open settings** / **Retry** |
| Share crashes | Ensure FileProvider authority `${applicationId}.fileprovider` and `@xml/file_paths` are in the final APK manifest |
| `buildozer` not found | `pip3 install --user buildozer` and ensure `~/.local/bin` is on `PATH` |
| Corrupt / half-built p4a venv (`capture_logging`) | Always delete `.buildozer/android/platform/build-*/build/venv` before buildozer (never cache it). If still broken, wipe `.buildozer` or clear Actions `buildozer-v2-*` cache |

**NumPy on Android vs desktop:** p4a’s default numpy is **2.x**, which may differ from an older desktop pin. After bumping Android recipes, run `python -m unittest discover -s tests` against the latest numpy on desktop to confirm `/core` still passes (result logged in `memory.md`).

## Permissions

Declared in `buildozer.spec` / AndroidManifest (via Buildozer):

| Permission | Why |
|------------|-----|
| `CAMERA` | Live Camera / Lens — request at runtime with rationale + settings fallback |
| `RECORD_AUDIO` | **Not** in the final APK — camerax_provider may inject it; `p4a_hook.py` strips it (we never record) |
| `READ_MEDIA_IMAGES` (API 33+) | Fallback gallery access on older flows |
| `READ_EXTERNAL_STORAGE` | Pre-13 gallery fallback |
| `WRITE_EXTERNAL_STORAGE` | Legacy pre-10 only; **not** required for MediaStore saves on Android 10+ |
| `INTERNET` | Optional; keep off unless a feature needs it |

### Photos pick & save (Android)

| API | Pick | Save |
|-----|------|------|
| **13+ (API 33+)** | `MediaStore.ACTION_PICK_IMAGES` via `PythonActivity.mActivity.startActivityForResult` + `android.activity.bind(on_activity_result=…)` (unbind after). **No** `READ_EXTERNAL_STORAGE`. | `MediaStore` insert with `RELATIVE_PATH=Pictures/ColorSight`, `IS_PENDING` clear → “Saved to your gallery” |
| **10–12** | Fallback `ACTION_GET_CONTENT` + `CATEGORY_OPENABLE` chooser (also used if Photo Picker intent fails) → URI → app cache | Same MediaStore path; no `WRITE_EXTERNAL_STORAGE` |
| **≤9** | May need `READ_EXTERNAL_STORAGE` (`ensure_read_images_permission`) | MediaStore or `getExternalFilesDir` fallback |

URI copy: `ContentResolver.openInputStream` → temp under app `getCacheDir()/ColorSightPick/`, then existing EXIF + resize pipeline. Share staging uses `getCacheDir()/ColorSightShare/` (FileProvider `cache-path`). Errors always surface a friendly status line and log a traceback to the diagnostics log.

Desktop: tkinter file chooser; save under `~/Pictures/ColorSight/`.

`pyjnius` + `android` are in `buildozer.spec` requirements for these bridges.

Unit tests: `python -m unittest tests.test_photo_io -v` (stream copy helper + friendly error paths).

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

**Verified on desktop (this repo):** unit suite (incl. `tests.test_photo_io`), trivector/photos/camera smokes, Welcome/Home/Profile/Settings UI logic.

**Not verified without a real device / APK build** — please run these yourself:

### Photos on a real phone (pick / save / share)

1. Install a fresh APK (`adb uninstall org.colorsight.colorsight` then `adb install …`).
2. Complete or load a correction profile (Photos needs one).
3. **Pick:** Photos → **Choose a photo** → system Photo Picker (Android 13+) or content chooser opens. Select an image → preview appears. Cancel should clear without a crash. If something fails, a friendly status appears (not a silent no-op) — open **Settings → Debug → View recent log** for the traceback.
4. **Save:** With Corrected/Simulation/Original, tap Save → status **“Saved to your gallery”**. Open the phone Gallery / Photos app → album **ColorSight** (`Pictures/ColorSight`) and confirm the image is there.
5. **Share:** Tap Share → system share sheet opens with the image. Send to Files / WhatsApp / Drive. If the sheet never opens, check the log for FileProvider errors and that CI’s FileProvider step passed for that build.
6. **Comparison:** Save/Share “How I see it” card the same way.

### Diagnostics log

- In-app: **Settings → Debug → View recent log** (no filesystem paths shown in the UI).
- Failures from pick/save/share write full tracebacks here (`colorsight` logger / rotating file under `user_data_dir`).

### Broader device checks

- [ ] APK installs (`adb install`) and opens without crash
- [ ] First launch → Welcome → color test; later launch → Home
- [ ] Android back button returns to Home from feature screens
- [ ] Floating nav + safe areas on a notched phone; nothing under the nav
- [ ] Vision Test → Save profile; Profile shows type / severity / date / axes
- [ ] Photos pick / save / share steps above
- [ ] Camera / Lens device checklist above (live preview, not color bars; permission card; flip; capture; loupe)
- [ ] Record on-device FPS + frame size (Settings → Show camera FPS) into the Measured FPS table

## Known issues / notes

- **Buildozer on Windows**: use WSL2 (above); expect long first builds.
- **p4a 2026.05.09**: defaults to Python 3.14; keep recipe deps unpinned; constrain charset-normalizer via **`PIP_CONSTRAINT` / `constraints.txt`**; use NDK **28c** and **arm64-v8a only** (see troubleshooting).
- **APK is 64-bit only** (`arm64-v8a`) — covers almost all current phones; no `armeabi-v7a` slice.
- **Python 3.13 desktop**: if Kivy wheels fail, use 3.11/3.12 in the venv.
- **Camera**: Camera4Kivy + CameraX via `camerax_provider`; no Android synthetic fallback. Desktop OpenCV / labeled Test pattern only.
- **FileProvider / Camera packaging**: `assets/android/p4a_hook.py` chains CameraX + FileProvider; CI fails if FileProvider, CAMERA permission, or CameraX classes are missing.
- **Radius 999**: always clamp (see `design.md`).
- Soft shadows are layered rounded rects, not Material elevation.

## `buildozer.spec` highlights

- Title **ColorSight**; `org.colorsight.colorsight`; single **`version = 0.1.0`** (no `version.regex` / `version.filename`)
- Portrait; **`android.api = 35`** / min 24; **`android.archs = arm64-v8a`** (64-bit only); **`android.ndk = 28c`**
- Requirements: `python3,kivy,numpy,opencv,pillow,pyjnius,android,camera4kivy,gestures4kivy` — no old kivy/numpy/pillow `==` pins; charset-normalizer via `constraints.txt` + `PIP_CONSTRAINT`
- CAMERA (+ media/storage); no RECORD_AUDIO in the final manifest (stripped by `p4a_hook.py`); CameraX via vendored `camerax_provider`; FileProvider + CameraX via `p4a.hook`; AndroidX; icon / adaptive / cream splash
- Cloud CI: FileProvider + CAMERA + CameraX APK checks (file-based grep, no pipefail false fails); APK artifact `if: always()`; failure log artifacts (3-day retention)
