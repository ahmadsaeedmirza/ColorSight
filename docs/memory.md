# Memory log

Newest entries first. Append after every prompt per `rules.md`.

---

## 2026-11-17 — Camera black despite uploads + clipboard no-op

**Prompt:** Still black on phone and laptop (webcam LED on); copy does nothing. Suspect no real change.

**Root cause (laptop proof):** `upload_ms` / timing logs showed frames were arriving — nested `RenderContext` FS blit painted **black** while Photos’ `rgb_to_texture` works. Clipboard: Kivy/SDL often silent no-op on Windows; Android needs UI-thread `ClipData`.

**Fix:** `LivePreviewStage` uses CPU `apply_matrix_shader_emulation` + `rgb_to_texture` (same matrix math as core; no broken GPU FBO). `clipboard_util`: Win32 CF_UNICODETEXT → Kivy → tkinter; Android ClipData + wait; status line under Copy button. No `/core` changes. No commit.

---

## 2026-11-17 — Camera/Lens black feed + log Copy broken

**Prompt:** Camera + Lens still black (“Starting camera…”); Recent log Copy to clipboard does nothing.

**Cause:** Full-size Preview at **opacity 0** still maps to Android view alpha 0 → CameraX/analyze never delivers frames. `connect_camera` could also run before Preview had a real layout size. Log copy used Kivy `Clipboard.copy` alone (Android ClipboardManager UI-thread race / silent fail) with no button feedback.

**Fix:** Preview **opacity 1** behind opaque stage; retry connect until size ≥32 px (~2 s); first-frame clears status; no-frame timeout 5 s; Camera header uses `NEUTRAL_TEXT`. New `clipboard_util.copy_text` (pyjnius `ClipData` on UI thread + Kivy fallback) with Copied/Copy failed on the button. Docs + `tests/test_clipboard_util.py`.

---

## 2026-11-16 — Vision Test tutorial glyphs + spacing

**Prompt:** Tutorial missing arrow icons / cramped pad; hue “red → violet” missing middle glyph; faint “Vision Test” title.

**Cause:** Tutorial tip + practice used Lexend Unicode arrows (`↑←↓→`); hue subtitle used `→` — Lexend has no those glyphs on Android (tofu). Header used theme `Colors.text` on cream `NEUTRAL_BG` (invisible in dark theme). Practice `PrimaryButton` keys overflowed a too-short inverted-T row.

**Fix:** Material Icons via `Icon` / `ArrowKey` (same as real ArrowPad); hue copy “red to violet”; `ScreenHeader` optional `title_color` / back neutrals on Test; practice pad uses `ARROW_KEY_DP` + `AnchorLayout` centering. Docs updated.

---

## 2026-11-16 — Lens loupe name pill contrast

**Prompt:** Lens (Camera+loupe) — “light gray” label invisible on white pill; ask if Camera fixes apply.

**Answer:** Black feed + system bars share Camera’s path (Lens is loupe state on Camera). Name pill was separate: white pill + dark-theme `Colors.text`. Fix: `NEUTRAL_TEXT` on loupe name label.

---

## 2026-11-16 — Photos action contrast + spacing

**Prompt:** Photo correction — “Choose another” text invisible; buttons overlapping / cramped.

**Cause:** White secondary button used `Colors.text` (light in dark theme). Action row fixed at 48dp while `PrimaryButton` grows past 52dp → overlap.

**Fix:** `NEUTRAL_TEXT` on white button; stack Choose another / Export vertically with synced height; brighter inactive mode chips; Strength labels use neutral text on cream surface. Docs updated.

---

## 2026-11-16 — Version sync 0.1.1 (About + APK)

**Prompt:** Manage the version shown in the app.

**Fix:** Bump `colorsight.__version__` and `buildozer.spec` `version` to **0.1.1** (must stay identical). Settings → About shows `ColorSight v{__version__}`. Preflight fails if they drift.

---

## 2026-11-16 — Theme system bars (kill white top/bottom chrome)

**Prompt:** White status + gesture bars on dark theme Camera screenshot.

**Fix:** `apply_system_bars(resolved)` sets Android status/nav bar colors to `Colors.bg` + icon contrast flags; `Window.clearcolor` stays in sync. Called from theme apply + first frame.

---

## 2026-11-16 — Camera black preview (full-size Preview + deferred connect)

**Prompt:** Camera screen chrome visible but feed solid black; fix camera only first.

**Cause:** Tiny 2×2 opacity-0 Camera4Kivy Preview gave CameraX no real surface; `connect_camera` could also run too early.

**Fix:** Full-bleed invisible Preview behind `LivePreviewStage`; `connect_camera` on next Clock tick; 2.5 s no-frame → error card. Docs updated.

---

## 2026-11-16 — Fix splash→black screen (verify before APK)

**Prompt:** APK still splash then black; previous crash-proof work did not fix it. Do not push.

**Root cause:** Splash dismissed early while `RootShell` eagerly imported every screen (`screens/__init__` → TestScreen → `core`/cv2 + Camera). Dark `Window.clearcolor` left an empty GL frame. Layout watchdog treated stuck **100×100** screens as OK.

**Fix:** Lazy `screens/__init__`; essential-first build (welcome/home/settings) then deferred heavy screens; cream clearcolor + Android `loadingscreen` until first sane frame; force SM/current screen to `Window.size`; font path resolve + Label probe → Roboto; tighter layout probe; nav/`ensure_screen` for deferred targets. Verified with `test_startup_resilience` + preflight (no push).

---

## 2026-11-16 — Android startup crash-proof + blank UI diagnosis

**Prompt:** APK showed splash then only themed background (no screens). ExceptionHandler PASS hid errors. No `/core` / staircase / scoring / assertion changes. Build safety unchanged.

**Impl:** Startup breadcrumbs (flushed); `build`/`rebuild_ui` try/except → plain fallback screen (Copy / Reset prefs / Try again); exception guard counts early faults + 3 s layout watchdog; safe_area clamps + pyjnius try/except (defaults 28/16); theme → Light on failure; GPU shader lazy on Camera enter with CPU fallback; RootShell fills window (`size_hint` + SM sync). **Root cause of blank themed background:** unregistered Lexend* font names → every Label raises `File … not found` → all screens fail → only RootShell bg. Fix: verify TTF files, fall back to Roboto names; empty SM raises into fallback UI. Tests: `tests/test_startup_resilience.py`. Docs updated.

---

## 2026-11-16 — Preflight unit tests need opencv-headless

**Prompt:** After xvfb fix, unit-test step still exited 1 (truncated log showed only FileProvider lines). Cause: preflight pip installed kivy/numpy/pillow but **not OpenCV** — `core` tests import `cv2`. No app logic changes.

**Fix:** Install `opencv-python-headless` in preflight; keep `COLORSIGHT_SKIP_GUI=1` on CI; clearer `run_unit_tests` failure summary. Docs updated.

---

## 2026-11-16 — Fix preflight headless X-server abort

**Prompt:** GHA `preflight` died with “Couldn't connect to X server” / exit 102 when Kivy imported a Window on ubuntu; `build` never started. No `/core` / vision-test / app / assertion changes.

**Fix:** apt xvfb + SDL/GL in preflight; unit tests via `xvfb-run -a -s "-screen 0 1280x800x24"` with `COLORSIGHT_HEADLESS=1`. `tools/preflight.py` uses a static Kivy builtin list (optional `kivy.factory` only — never creates a Window). GUI tests lazy-import + `tests.gui_guard.ensure_kivy_window` → SkipTest if Window fails under headless. `run_unit_tests.py` never imports GUI modules when `COLORSIGHT_SKIP_GUI=1`. Docs: CI headless notes; GUI smokes local-only.

---

## 2026-11-15 — Android CI preflight guardrails

**Prompt:** Stop cloud builds failing for avoidable reasons. No `/core` / vision-test / app behavior / existing-test changes.

**Added:** `tools/preflight.py` (spec/pins/arch/ndk/api/permissions/assets/hooks/constraints, CRLF, compileall, Kivy pitfalls, fonts/includes; warns android-wheel risks). `tools/run_unit_tests.py` skips GUI modules when `COLORSIGHT_SKIP_GUI=1`. `.gitattributes` forces LF. `tools/build_android.sh` runs preflight first.

**Workflow:** `preflight` job (Py 3.11) → `build` `needs: preflight`; concurrency cancel; cache `buildozer-v2-<hash(spec+constraints+camerax_provider/**)>` never venv; `clean_cache` dispatch input; logs + APK `if: always()`; file-based packaging greps; `GITHUB_STEP_SUMMARY`; actions → checkout/setup-python/cache/upload@v7, setup-java@v6 (Node 24).

**Docs:** production “Before you push” + pitfalls table; rules; this entry.

---

## 2026-11-15 — Android runtime: picker, Lens crash, GPU camera

**Prompt:** Three real-phone fixes — Photos picker no-op; Lens nav crash; smooth camera via GPU. No `/core` / staircase / scoring / existing-test edits. Build safety: unpinned reqs + add pure-Python `androidstorage4kivy` only; no PIP_CONSTRAINT/api/ndk/archs changes; no CRLF in .sh/.spec/.yml/.py.

**Photos:** Immediate “Opening gallery…” + `photos:` diagnostics on every step. Prefer `androidstorage4kivy` Chooser + `SharedStorage.copy_from_shared`; legacy pyjnius picker automatic fallback. Save prefers `copy_to_shared` (Pictures / ColorSight) then MediaStore. Settings → Debug → **Test photo picker**.

**Lens:** Not a mid-transition redirect. `RootShell._navigate("lens")` → Camera + `Clock.schedule_once` → `set_loupe_enabled`; Lens nav highlighted while loupe on. Global `ExceptionHandler` logs + “Something went wrong” + `PASS`. Regression: `tests/test_lens_nav.py`.

**Camera GPU:** `camera_gpu.py` + `LivePreviewStage` RenderContext FS `mat3` (identity/correction/simulation ≡ `core._apply_matrix`). One reused RGBA texture; latest-frame-wins; Strength = uniform only; loupe zoom from CPU original, name ~5 Hz; timing r/u/d + fps every 5 s. Unit: `tests/test_camera_gpu.py` (≤1/255 vs core).

**Packaging / docs:** `androidstorage4kivy` in `buildozer.spec`; architecture/production/rules + this entry.

---

## 2026-11-15 — Theme rebuild, safe insets, chip scroll, test tutorial

**Prompt:** Real-phone UI: theme not applying fully; status-bar overlap (api 35); Home chips start scrolled; skippable Vision Test tutorial. No `/core` / staircase / scoring / existing-test changes.

**Theme:** `ThemeController.apply` → tokens + `Window.clearcolor` + `ColorSightApp.rebuild_ui()` (recreate SM/screens/nav; return to Settings). System night mode on start/resume. Test: `tests/test_theme_rebuild.py`.

**Insets:** `safe_area.refresh_safe_insets` → `Spacing.safe_top` / `safe_bottom`; headers/Home/Welcome/nav; phone-sim 28/24 dp.

**Chips:** `ChipRow.reset_scroll()` on Home enter + rebuild.

**Tutorial:** `test_tutorial.py` + prefs `test_tutorial_seen`; Skip; practice UI-only; Replay in Settings/checklist. Neutral BG.

**Verify:** `SMOKE_PHONE_SIM … insets:top=28:bottom=24` + theme rebuild. Docs/rules updated.

---

## 2026-11-15 — Fix CI packaging-check false fail (run #4)

**Prompt:** Run #4 APK built + CameraX strings present, but “Verify FileProvider + Camera” failed. Cause: `set -euo pipefail` + `echo \| grep` Broken pipe. No `/core` / vision-test / app / existing-test changes.

**Fix:** File-based greps (`apk_manifest_dump.txt`, `apk_dex_strings.txt`); display pipes `|| true`. APK upload `if: always()` when `bin/*.apk` exists. Strip unused `RECORD_AUDIO` from final manifest in `p4a_hook.py` (camerax_provider adds it; we never record). Docs + `rules.md`. Commit + push `master`.

---

## 2026-11-15 — Fix CI p4a build/venv pip corruption (run #3)

**Prompt:** GHA run #3 failed: cache restored `.buildozer` including `build/venv`; p4a ran `python -m venv` over it; `pip install -U pip` → `ImportError: cannot import name 'capture_logging'`. Same on WSL re-runs. No `/core` / vision-test / app / existing-test changes. **Do not commit** (user pushes).

**Fix:** Workflow deletes `.buildozer/android/platform/build-*/build/venv` before build; cache paths exclude that venv; cache key prefix → `buildozer-v2-` (poisoned `buildozer-` caches unused). Same `rm -rf` in `tools/build_android.sh`. `PIP_CONSTRAINT` unchanged.

**Docs:** `production.md` pitfalls; `rules.md`; this entry.

---

## 2026-11-15 — Real Android Camera / Lens (Camera4Kivy)

**Prompt:** APK Camera/Lens showed synthetic color bars — Android source was a stub with silent FakeFrameSource fallback. Wire real camera; no `/core` / vision-test / existing-test changes.

**Decision:** Camera4Kivy + vendored `camerax_provider/` (CameraX) for p4a 2026.05.09 / Py 3.14 / api 35 / arm64-v8a. No silent Android fake. Desktop: OpenCV, else labeled “Test pattern”.

**Impl:** `AndroidCameraSource` — tiny invisible `Preview`, `connect_camera(enable_analyze_pixels=True, analyze_pixels_resolution=640, enable_video=False)`, RGBA→RGB (+ front mirror), latest-frame drop → existing pipeline. Permission callback; error card (permission / no camera / start failed) + Retry / Open settings. Flip / disconnect on leave/pause. Capture → MediaStore. FPS debug shows `N fps · W×H`. `camera_event` logs to diagnostics.

**Packaging:** `gestures4kivy` in requirements; `p4a.hook` = `assets/android/p4a_hook.py` (CameraX before + FileProvider after). CI fails if CAMERA or CameraX classes missing.

**Tests:** `tests/test_camera_source.py` (session state + fakes). Docs: architecture decision, production device steps, rules, phases. User commits. On-device FPS row in production.md left blank for device fill-in.

---

## 2026-11-15 — Photos Android pick / save / share (real phone)

**Prompt:** APK “Choose a photo” was a silent no-op. Fix Photo Picker + URI→cache, MediaStore save, FileProvider share, CI manifest gate, unit tests, docs. No `/core` / vision-test / existing-test changes.

**Pick (`photo_io.py`):** `PythonActivity.mActivity.startActivityForResult` + `android.activity.bind(on_activity_result=…)` / unbind. API 33+: `MediaStore.ACTION_PICK_IMAGES` (no chooser wrapper). Fallback: `ACTION_GET_CONTENT` + `CATEGORY_OPENABLE`. `content://` → `ContentResolver.openInputStream` → app `cache/ColorSightPick/`; then EXIF/resize pipeline. Failures → friendly UI + log traceback (never silent). Desktop tkinter unchanged.

**Save / Share:** MediaStore `RELATIVE_PATH=Pictures/ColorSight` → “Saved to your gallery”. Share staging under `cache/ColorSightShare/`; FileProvider authority `org.colorsight.colorsight.fileprovider` + `FLAG_GRANT_READ_URI_PERMISSION`.

**Packaging:** `android.enable_androidx`, `android.gradle_dependencies=androidx.core:core:1.12.0`, `android.add_resources` → `@xml/file_paths`, `p4a.hook=assets/android/p4a_fileprovider_hook.py` (reliable `<provider>` inject; optional `extra_manifest_application_xml`).

**CI:** After APK build, dump manifest / strings and **fail** if `fileprovider` missing; upload dump artifact.

**Tests:** `tests/test_photo_io.py` — `copy_stream_to_path` + pick/save/share error paths (29 tests OK with image/photos pipeline).

**Docs:** `architecture.md`, `production.md` (device pick/save/share steps + Settings → Debug → View recent log), `rules.md`, this entry. User commits.

---

## 2026-11-15 — Phone UI batch: theme, chips, camera, diagnostics

**Prompt:** Real-phone UI batch (1080×2400): black transition flash; Home chip centering/scroll; Vision Test pressed states; Camera layout/loupe clip; System/Light/Dark theme with neutral accuracy surfaces; on-device log viewer; GHA action majors. No `/core` / vision-test logic / scoring / existing-test changes. **Do not commit** (user pushes).

**Fixes:** Opaque screen + root BGs; `Chip` 40 dp + centered `text_size`; chip row bleeds to right edge; ArrowKey blue press ≥120 ms; peach `CantSeeButton` + `visibility_off`; Camera margins/z-order/loupe stencil + centered start; `ThemeController` + dark tokens; Test/Photos/Camera stay `NEUTRAL_BG`; rotating log + Settings “View recent log”; Actions checkout/cache/java/python/upload → v5/v6; `tests/test_chip_centering.py`.

---

## 2026-11-15 — Android full-screen layout + API 35

**Prompt:** APK UI stuck in ~390 px bottom-left box on 1080×2400; Welcome clipping/overlap; Play Protect older-Android note; phone-density desktop sim. No `/core` / vision-test / test changes.

**Cause / fix:** Desktop `Window.size=(390,844)` applied on Android. `main.py` sets Config graphics **only** if `platform not in ('android','ios')`; `app.py` no longer sets `Window.size`. `PrimaryButton` wraps label + grows height; Welcome tip above arrow, cards `auto_height=True`.

**Build:** `android.api = 35` (min 24). Phone sim: `tools/run_phone_sim.py` + `tools/smoke_phone_sim.py` (540×1200 @ density 1.375).

**Docs:** `production.md` pitfalls (layout box, Play Protect, uninstall for new debug key), phone-sim section; `design.md` Welcome; `rules.md` / others. Commit + push `master`.

---

## 2026-11-15 — Fix CI charset-normalizer via PIP_CONSTRAINT

**Prompt:** GHA run #1 failed at p4a pip install — dry-run resolver ignored `buildozer.spec` pin and picked charset-normalizer 3.5.2’s `android_24_arm64_v8a` wheel; host pip rejected it. No `/core` / vision-test / test changes.

**Fix:** Repo-root `constraints.txt` (`charset-normalizer==3.4.9`); workflow sets `PIP_CONSTRAINT` on the buildozer step + prints constraints before build; removed pin from `buildozer.spec` requirements (now exactly `python3,kivy,numpy,opencv,pillow,pyjnius,android,camera4kivy`). Failure artifacts: last **1500** lines + full `buildozer-ci.log` (retention 3 days).

**Docs:** `production.md` pitfalls/troubleshooting updated (p4a drops pip-module pins → use `PIP_CONSTRAINT`); `rules.md` / `architecture.md` / `phases.md` / this entry. Commit + push to `master`.

---

## 2026-11-15 — GitHub Actions cloud Android build

**Prompt:** Cloud Android build via GitHub Actions; never require local builds. No `/core` / vision-test / existing-test changes.

**Workflow:** `.github/workflows/android.yml` — `workflow_dispatch` + push to `build-apk`; `ubuntu-22.04`; timeout 360; free disk; Java 17 + apt deps; `buildozer` + `cython==0.29.36`; cache `~/.buildozer` + `./.buildozer`; `buildozer -v android debug`; artifact `colorsight-apk`; on failure upload last 500 log lines.

**Spec / repo hygiene:** `buildozer.spec` single `version = 0.1.0` (removed regex/filename); requirements/arch/ndk/permissions/FileProvider unchanged as required. `.gitattributes` LF for `buildozer.spec` + `tools/*.sh`. `.gitignore` for `.venv`, `.buildozer`, `bin`, `dist`, `debug`, `__pycache__`, `*.pyc`. Deleted root `debug_*.png`.

**Docs:** `production.md` **Cloud build** section (run, download APK, failure log, pitfalls: FreeType, NDK 28c, charset-normalizer pin, corrupt venv); WSL kept as fallback. `rules.md` / `architecture.md` / `phases.md` / this entry.

---

## 2026-11-15 — Pin charset-normalizer==3.4.9 for Android build

**Prompt:** Add `charset-normalizer==3.4.9` to `buildozer.spec` requirements — p4a resolves 3.5.2 to an `android_24_arm64_v8a` wheel that host pip cannot install. No `/core` / vision-test / test changes.

**Fix:** `requirements = python3,kivy,numpy,opencv,pillow,pyjnius,android,camera4kivy,charset-normalizer==3.4.9` (only this pin; other deps stay unpinned).

**Docs:** `production.md` troubleshooting row; highlights + `rules.md` / `architecture.md` / `phases.md` / this entry.

---

## 2026-11-15 — NDK 28c + arm64-v8a only

**Prompt:** Set `android.archs = arm64-v8a` and `android.ndk = 28c` (p4a 2026.05.09 recommended NDK; 25b fails NumPy 2.3 libc++). Document troubleshooting; note 64-bit-only APK. No `/core` / vision-test / test changes.

**`buildozer.spec`:** `android.ndk = 28c`; `android.archs = arm64-v8a` (dropped `armeabi-v7a`).

**Docs:** `production.md` — troubleshooting “NumPy fails with no template named unordered_map → use NDK 28c”; APK name / highlights / known issues updated for 64-bit-only; FreeType path notes `build-arm64-v8a`. `rules.md`, `architecture.md`, `phases.md`, this entry.

---

## 2026-11-15 — buildozer.spec unpinned for p4a 2026.05.09 / Python 3.14

**Prompt:** Fix Android `requirements` for current python-for-android (release 2026.05.09, default Python 3.14): remove version pins; document FreeType Savannah workaround + pin-breakage; confirm `/core` on latest numpy. Leave desktop `requirements.txt` alone; no `/core` / vision-test / existing-test changes.

**`buildozer.spec`:**  
`requirements = python3,kivy,numpy,opencv,pillow,pyjnius,android,camera4kivy` (no `==` pins). Old `kivy==2.3.0` / `numpy==1.26.4` / `pillow==10.4.0` break on 3.14; numpy pin also fails because the recipe looks for git tag `1.26.4` vs real tag `v1.26.4`.

**Docs:** `production.md` troubleshooting rows for (1) FreeType via SourceForge `.tar.gz` + `.mark-…` marker, (2) version pins on new p4a; highlights + known-issues updated. `rules.md` Android-requirements note. Desktop `requirements.txt` untouched.

**NumPy check:** Desktop venv already on / upgraded to **numpy 2.5.4**; `python -m unittest discover -s tests` → **76 OK**. `/core` works with numpy 2.x (same major family p4a will pull by default).

---

## 2026-11-14 — UI-only: chips, D-pad, headers

**Prompt:** Fix Home Chip wrap (“Camer/a”); inverted-T Vision Test D-pad + desktop arrow keys; header back/title gap + Settings top inset; narrow desktop pass; update docs. Do **not** touch `/core`, staircase, thresholds, scoring, or existing tests.

**Chips:** `Chip` no longer binds `text_size` to widget size (that forced wrap). Width = texture + 18 dp pad/side; `ChipRow` in horizontal `ScrollView` (`bar_width=0`). Callbacks renamed `select_cb` / `change_cb`. Toolbar `_ModeChip` / `_CamChip`: `shorten` + `max_lines=1`.

**D-pad:** `ArrowPad` keyboard layout (Up; Left·Down·Right), 72/8 dp; same orient / can't-see callbacks. `TestScreen` binds `Window.on_key_down` (273–276) only during trivector. Compact trial column (~570 dp) fits 360×640 without scroll.

**Headers:** new `ScreenHeader` (`header_gap`, optional `screen_top`) on Test / Photos / Camera / Settings / Profile. Tokens: `Spacing.screen_top`, `Spacing.header_gap`.

**Other:** `PastelCard.select_cb`, `FloatingNavBar.navigate_cb`; `RootShell` builds nav before setting `sm.current` (Home launch crash). Smokes: `tools/smoke_ui_polish.py`, `tools/smoke_ui_flow.py`. Unit tests OK in venv (76).

---

## 2026-11-14 — Phase 1 final polish (Profile, Settings, build)

**Prompt:** Profile + Settings; app-wide polish (first-run, Home, back); Android buildozer/icons/WSL/`build_android.sh`; final review + README. No core math / vision-test logic / scoring / existing test breakage.

**Profile:** Hero card, SeverityBar, AxisBars when thresholds stored, swatch strip, fine-tune with confirm (only overwrite), reset to test severity, clear with confirm. Optional profile JSON metadata via UI save path.

**Settings:** About / Privacy / Display tips / FPS toggle. **Welcome:** CTA → Test; mark onboarding done. **Home:** chips + avatar→Profile, menu→Settings, no search. **App:** first-run prefs, back key. **Build:** icon/splash/adaptive, `buildozer.spec` pins, `tools/build_android.sh`, WSL steps + device checklist honesty in production.md. **README.md** + Phase 1 marked complete; Phase 2 Shizuku listed only.

---

## 2026-11-14 — Photos split-0 default + Camera/Lens

**Prompt:** Photos filter-on-by-default (divider 0%), disk profile reload + strength tests; Camera + Lens shared live pipeline; loupe/`name_color`; freeze/capture; FPS toggle. No `/core` changes.

**Photos:** Default Corrected; `photos_default_split()=0` (full filtered; handle left, ≥44 dp inside bounds); reset split on Corrected/Simulation/new pick; one-time compare hint; always `CorrectionProfile.load(profile_path())` on enter; log `photos_strength …`; tests for 0.91→91 and 1.0→100.

**Camera/Lens:** `camera_source` (OpenCV / Fake / Android+Camera4kivy stub), `camera_pipeline` helpers, `CameraScreen` + `LoupeOverlay`, `LensScreen` redirects with loupe on. Frame drop loop, pause/resume, Settings FPS toggle.

**Verified:** 29 unit tests OK; `SMOKE_PHOTOS_OK`; `SMOKE_CAMERA_OK camera_default_ok … loupe_ok freeze_capture_ok lens_redirect_ok shutdown_ok`.

---

## 2026-11-14 — Photos Strength, divider, save/share, comparison

**Prompt:** Fix Strength default (91 not 100) + reset; divider hide on Original, show on Corrected/Simulation with labels + 44 dp hit; verify correction MAD; mode-aware Save/Share; “How I see it” comparison card; Simulation tuning hint. No `/core` changes.

**Fixes**
- Strength from `severity_for_slider(profile.severity)` on load/pick; “Reset to my result” when preview ≠ saved; hint copy under Strength.
- Divider: `divider_visible` — Original off; Corrected/Simulation left=original / right=mode; corner labels; 44 dp handle.
- Simulation previously showed full-frame only (no split) — now uses `before_after_split` like Corrected. Correction MAD unit test (deutan 0.91) passes (core apply_* OK).

**Save/Share**
- Save/Share export current mode at full res via `render_mode_rgb` + current Strength (profile JSON untouched).
- Android: MediaStore album + `ACTION_SEND` FileProvider (`assets/android/file_paths.xml` + snippet). Desktop share → save + “Saved to your gallery”.
- Export comparison card (`build_comparison_card`, longest ≤2048).

**Verified:** `tests.test_photos_pipeline` + image_pipeline OK; `SMOKE_PHOTOS_OK … profile_strength_ok modes_divider_ok strength_reset_ok exports_ok`.

---

## 2026-11-14 — Fix Photos toolbar mode crash (`on_mode` None)

**Prompt:** Tapping Original/Corrected/Simulation crashed with `TypeError: 'NoneType' object is not callable` (photo_widgets `_tap_mode` → `mode=` → Kivy observer None).

**Cause:** Kivy auto-calls `on_<prop>` when a property changes. `PhotoModeToolbar` had both `mode = StringProperty(...)` and `on_mode = ObjectProperty(None)` — so dispatch invoked `None`. Same trap existed for `split` / `on_split`.

**Fix:** Rename callback props to `mode_cb`, `save_cb`, `split_cb`, `change_cb`. Real `on_mode` / `on_split` methods sync UI + `_invoke` optional cbs. Guard all callbacks with `callable`. Mode taps update highlight + cached preview.

**Smoke:** `tools/smoke_photos_ui.py` now taps every toolbar mode, severity bar, before/after split, then save → `SMOKE_PHOTOS_OK … toolbar_modes_ok severity_ok split_ok save_ok`.

**Docs/rules:** Kivy `on_<prop>` naming pitfall noted.

---

## 2026-11-14 — Photos screen (image correction)

**Prompt:** Build Photos — profile gate, Android Photo Picker / desktop chooser, before/after viewer, Original|Corrected|Simulation + preview severity (no profile overwrite), ~1080 preview + bg thread/cache/debounce, full-res MediaStore/Pictures save, pastel UI, pipeline unit tests + desktop smoke. Do **not** change `/core` math, vision test, scoring, or existing tests.

**Added**
- `colorsight/image_pipeline.py` — EXIF transpose load, resize longest≤1080, RGB↔BGR, before/after split, JPEG95/PNG encode
- `colorsight/photo_io.py` — desktop tk chooser; Android Photo Picker + URI→temp; MediaStore album ColorSight; friendly “Saved to your gallery”
- `colorsight/screens/photos.py` + `photo_widgets.py` — `BeforeAfterViewer`, `PhotoModeToolbar`, `PreviewSeverityBar`, `LoadingShimmer`
- `tests/test_image_pipeline.py` (9); `tools/flow_photos.py`; `tools/smoke_photos_ui.py`
- Icons: `save`, `drag_handle`, `add_photo`, `tune`, `check`

**Behavior:** No profile → CTA to Test. Severity uses `CorrectionProfile.create` in memory only. Corrected mode = left original / right corrected with white handle. Cache makes mode toggles instant.

**Verified:** 54 unittest OK; `FLOW_PHOTOS_OK`; `SMOKE_PHOTOS_OK no_profile_ok profile_ok pick_ok modes_ok save_ok`. Core untouched.

**Docs:** architecture, design, production (picker/MediaStore/permissions), phases, rules, memory.

---

## 2026-11-14 — Vision Test UI polish (D-pad, stim, results)

**Prompt:** UI-only — D-pad centering/overlap; “Question N”; crisp stim + less lag; results disclaimer/axis labels/severity number. No `/core` or test changes.

**D-pad:** `ArrowKey` FloatLayout (76 dp, clamped radii, shadow, press opacity); 3×3 cross with empty center; full-width “I can't see it”; gap under prompt.

**Trial:** Persistent shell (no tree rebuild); label “Question N”; stim `size=512` + linear texture blit reuse; timeout unchanged.

**Results:** `PastelCard(auto_height=True)` disclaimer wrap; `AxisBars` rows with Protan/Deutan/Tritan + ×cutoff + 1.0× tick; `SeverityBar` shows “N / 100”.

**Timing (profiled on desktop flow):**

| Metric | Before (approx.) | After |
|--------|------------------|-------|
| UI tree per trial | Full `_clear` + rebuild ScrollView/pad/icons | Persistent shell |
| Texture apply | New texture each trial | Reused blit + linear filter |
| Blit-only avg | — | **~1.0 ms** |
| Total trial step avg (incl. core `next_trial` @ 512) | — | ~386 ms (dominated by stimulus generate, not UI) |

**Verified:** FLOW_OK at 360×640 and 900×700. Core/tests untouched.

---

## 2026-11-14 — Fix ArrowPad Icon.size crash

**Prompt:** Trivector start crashed with `ValueError: Icon.size must be a list or a tuple` from `ArrowPad._arrow` passing `size=dp(28)`.

**Fix:** `Icon` already exposes **`icon_size`** (default 24). ArrowPad now uses `Icon(icon=…, icon_size=28)`. Added a clear `TypeError` if numeric `size=` is passed. Audited all `Icon(...)` call sites — only ArrowPad was wrong.

**Verified:** Desktop flow Welcome → Home → Test checklist → trivector (arrows + can't see) → hue → results → save → `FLOW_OK`. 45 unit tests OK.

**Docs/rules:** Icon sizing rule in `design.md` / `rules.md`.

---

## 2026-11-14 — Replace plates with CCT Trivector

**Prompt:** Swap live Vision Test to Cambridge Colour Test (Trivector) for type + severity; keep `plates.py` + tests as legacy; keep hue step; model-observer calibration + accuracy tests; checklist/results UI; no engine math changes.

**Core:** New `core/trivector.py` — CIE u'v' D65 background, protan/deutan/tritan copunctals, Landolt C dot stimuli (`pack_circles_dense`), interleaved 4-AFC staircases (phone 8 / full 11 reversals), classification cutoffs, Machado model-observer calibration → severity curves. `CorrectionProfile` from `TrivectorResult.to_profile()`.

**UI:** Checklist → trials (arrows + can't see, 6 s timeout, ~190 dp C) → hue → results (severity label/bar, axis bars, disclaimer, save). Home card: “Trivector color check”.

**Tests:** `tests/test_trivector.py` (11). Full suite **45 OK**. `tools/flow_trivector.py` → `FLOW_OK`.

### Confusion matrix (true type × severity → estimated)

| true | sev | est type | est sev |
|------|-----|----------|---------|
| protanopia | 0.0 | normal | 0.00 |
| protanopia | 0.3 | protanopia | 0.30 |
| protanopia | 0.5 | protanopia | 0.50 |
| protanopia | 0.7 | protanopia | 0.70 |
| protanopia | 1.0 | protanopia | 1.00 |
| deuteranopia | 0.0 | normal | 0.00 |
| deuteranopia | 0.3 | deuteranopia | 0.30 |
| deuteranopia | 0.5 | deuteranopia | 0.50 |
| deuteranopia | 0.7 | deuteranopia | 0.70 |
| deuteranopia | 1.0 | deuteranopia | 1.00 |
| tritanopia | 0.0 | normal | 0.00 |
| tritanopia | 0.3 | tritanopia | 0.30 |
| tritanopia | 0.5 | tritanopia | 0.50 |
| tritanopia | 0.7 | tritanopia | 0.70 |
| tritanopia | 1.0 | tritanopia | 1.00 |

(Machado-calibrated threshold patterns; matching axis from calibration knots.)

---

## 2026-11-14 — Shape legibility only (counters / dots / recognizability)

**Prompt:** Fix over-dilated digit masks (3/9 blobs); smaller dots, open counters; add color-independent recognizability tests; contact sheet + figure-only previews; re-run tests; report per-plate pass/fail under normal/protan/deutan/tritan; update docs. Do **not** change confusion palettes or existing ΔE validation gates.

**Shape changes (`core/plates.py`):**
- Lexend-SemiBold ~60% (Bold fallback); **no mask dilate**; light erode; figure assignment on **inset** ink so disks cannot fill counters.
- Smaller radii (~stroke/7), air gap between dots, crisp ellipse paint (no AA bloat).
- Helpers: `clean_digit_mask`, `digit_recognizability`, `count_digit_holes`, `RECOG_MARGIN=0.08`.

**Tests / preview:** `tests/test_plate_recognizability.py`; `tools/preview_plates.py` writes `contact_sheet.png` + `{id}_figure_only.png`.

**Verified:** 34 unit tests OK. Palettes/ΔE gates unchanged and still pass.

### Digit readable under simulation (PASS = expected digit; FAIL = designed miss)

| plate | digit | axis | normal | protan | deutan | tritan |
|-------|-------|------|--------|--------|--------|--------|
| c1 | 8 | control | PASS | PASS | PASS | PASS |
| h1 | 5 | hidden_rg | PASS | FAIL | FAIL | PASS |
| h2 | 2 | hidden_rg | PASS | FAIL | FAIL | PASS |
| h3 | 6 | hidden_rg | PASS | FAIL | FAIL | PASS |
| h4 | 9 | hidden_rg | PASS | FAIL | FAIL | PASS |
| h5 | 3 | hidden_rg | PASS | FAIL | FAIL | PASS |
| h6 | 7 | hidden_rg | PASS | FAIL | FAIL | PASS |
| cp1 | 4 | classify_protan | PASS | FAIL | PASS | PASS |
| cp2 | 1 | classify_protan | PASS | FAIL | PASS | PASS |
| cd1 | 5 | classify_deutan | PASS | PASS | FAIL | PASS |
| cd2 | 2 | classify_deutan | PASS | PASS | FAIL | PASS |
| cd3 | 6 | classify_deutan | PASS | PASS | FAIL | PASS |
| t1 | 3 | tritan | PASS | PASS | PASS | FAIL |
| t2 | 9 | tritan | PASS | PASS | PASS | FAIL |

**Totals:** normal **14/14 PASS**; protan **6 PASS / 8 FAIL**; deutan **5 PASS / 9 FAIL**; tritan **12 PASS / 2 FAIL**.

**Simulated respondents:** normal→normal, protanopia→protanopia, deuteranopia→deuteranopia, tritanopia→tritanopia.

**Shape check:** every plate `ok_match` + `ok_holes` under normal figure raster (margins ≥ 0.08).

---

## 2026-11-14 — Plate audit + validation + 3 UI fixes

**Prompt:** Fix unreadable plates (dense packing, bold mask, confusion palettes, metadata, ΔE/IoU tests, preview tool, scoring with inconclusive); UI: swatch black edge, friendly save text, nav Camera/FAB.

**Plates:** Rewrote `core/plates.py` — Lexend-Bold ~60% mask + heavy dilation, hex packing, equiluminant confusion fallbacks, `RenderedPlate` + `plate_metrics`. Battery roles: 1 control, 6 hidden RG, 2/3 classify, 2 tritan with expected_* table. Validation tests enforce ΔE/ΔL/figure count/stroke/IoU; `tools/preview_plates.py` → `debug/plates/` (gitignored).

**Scoring:** Expected-answer match rates + thresholds → normal/protan/deutan/tritan/**inconclusive**; `simulate_respondent` unit tests.

**UI:** Demo bands fill exact width; save message without path; `FloatingNavBar` five identical icon+label slots + FAB clamped inside pill.

**Verified:** 31 unit tests OK; FLOW_OK normal + save copy; previews written.

---

## 2026-11-14 — Fix ProgressBar / Kivy style.kv collision

**Prompt:** Crash on Test plates — `BuilderException` / missing `max` because custom `ProgressBar` collided with Kivy’s built-in. Rename, audit collisions, run full flow, document naming rule.

**Fix:**
- Renamed `ProgressBar` → `PillProgressBar` in `test_widgets.py` + `test_screen.py`.
- Audited `colorsight/widgets` + `screens`: only collision was `ProgressBar` (`CameraScreen` / `Icon` / `Chip` are fine).
- Also replaced deprecated `Image(allow_stretch/keep_ratio)` with `fit_mode`.
- Automated flow: Welcome → Home → Test intro → plates → hue → results → save → `FLOW_OK`.

**Docs/rules:** Never name custom widgets after built-in Kivy widgets.

---

## 2026-11-14 — Vision Test feature (plates, hue, scoring, results)

**Prompt:** Build Color Vision Test on Test screen — procedural Ishihara-style plates (no copyrighted images), 12–16 plate flow with numpad + can't-see, hue-arrangement severity step, scoring in `/core`, pastel results with before/after + Save profile + medical disclaimer. Update docs.

**Decisions:**
- 14-plate `DEFAULT_BATTERY` in `core/plates.py` (control, RG, protan, deutan, blue-yellow palettes); circle packing + OpenCV digit masks.
- Scoring in `core/scoring.py` → `TestResult` (normal / protanopia / deuteranopia / tritanopia + severity); hue MAD error blended into severity.
- UI state machine in `test_screen.py` with `test_widgets` (PillProgressBar, Numpad, HueStrip); profile via `CorrectionProfile` + `storage.profile_path()`.
- Explicit result disclaimer: screening only; phone screens vary.
- Spatial-hash packing so battery prep is ~2s at 360px.

**Files:** `core/plates.py`, `core/scoring.py`, `core/__init__.py`, `tests/test_plates_scoring.py`, `colorsight/screens/test_screen.py`, `test_widgets.py`, `storage.py`, all `/docs`, `rules.md`.

**Verified:** 27 unit tests OK; Test screen opens; battery gen ~2.4s.

**Deferred:** Profile screen loader, photos/camera/lens wiring.

---

## 2026-11-14 — Core color engine (`/core`) + unit tests

**Prompt:** Build pure-Python color engine (no UI): Machado CVD simulation, daltonization/correction, `CorrectionProfile` JSON, vectorized `apply_*`, `name_color`, tests in `/tests`, document math in architecture, update all docs.

**Decisions:**
- Package at project-root `core/` (not under `colorsight/`) so engine stays UI-free.
- Machado et al. 2009 tabulated matrices (0.0–1.0 step 0.1) with linear interpolation for in-between severity.
- Daltonization via Fidaner-style error shift; store composite \(C = I + E(I-S)\) on the profile for one matmul per frame.
- `name_color`: OpenCV Lab nearest-neighbor + HSV neutrals; small named palette.
- Tests: `unittest` discover in `/tests` (18 passing, including soft 720p timing).

**Files:** `core/*`, `tests/*`, `docs/*`, `rules.md`, `buildozer.spec` include `core/*`.

**Deferred:** Wiring engine into Kivy screens (test/photos/camera/lens), gamma-aware linear RGB path, on-device camera loop.

---

## 2026-11-14 — Shell visual bugfix (icons, pills, chips, nav, scroll)

**Prompt:** Fix Home screenshot issues — empty icon boxes, oval pills, black chip with invisible text, nav overflow, content under nav; same checks on Welcome. No features. Update all docs.

**Decisions / fixes:**
- Bundled **Material Icons** TTF under `assets/icons/` (Apache 2.0 `LICENSE` / `LICENSE.txt`); registered as `Fonts.icons`.
- Added `Icon` widget + `Icons` ligature tokens; replaced emoji/Lexend pseudo-icons (menu, search, nav, FAB `add`, arrows, avatar).
- Added `clamp_radius` / `clamped_radii` — every canvas radius uses `min(r, w/2, h/2)`; shadows use the same value.
- Chips: selected = dark fill + **white** Lexend label; unselected = white + dark label; vertical centering via `text_size` + border line.
- `FloatingNavBar` rebuilt as `FloatLayout`: width = screen − 2×18dp, equal slots, labels for all items, raised blue FAB contained in widget height for hit-testing.
- Home + placeholders: ScrollView with `Spacing.nav_clearance` (120) bottom padding; Welcome uses Material `arrow_forward`.
- Buildozer patterns updated to include `assets/icons/*`.

**Files touched:** `theme/*`, `widgets/*`, `screens/*`, `app.py`, `buildozer.spec`, `assets/icons/*`, all `/docs`, (policy still in `rules.md`).

**Verified:** Desktop smoke + Home nav fits parent with margins; Material ligature textures non-empty; selected chip label color white.

---

## 2026-11-14 — Phase 0: project setup, docs, design system, app shell

**Prompt:** Initialize ColorSight — docs policy, `/docs`, pastel design system, reusable widgets, ScreenManager shell (Welcome/Home + placeholders), desktop entry, Buildozer notes. No feature pipelines.

**Decisions:**
- Pure **Kivy** (no KivyMD) so pastel cards + floating pill nav match the notes-app reference without fighting Material defaults.
- Bundle **Lexend** (Regular/Medium/SemiBold/Bold) under `assets/fonts` (OFL).
- Design tokens live in `colorsight/theme/tokens.py`; widgets under `colorsight/widgets/`.
- Screen ids: `welcome`, `home`, `test`, `photos`, `camera`, `lens`, `profile`, `settings`.
- Phase 2 (SurfaceFlinger 4×4 matrix + Shizuku) documented only in `phases.md`, not implemented.
- Soft shadows via layered rounded rects; tap scale animations on interactive cards/buttons.

**Files created:**
- `rules.md`, `docs/*`, `requirements.txt`, `buildozer.spec`, `main.py`
- `colorsight/app.py`, `theme/*`, `widgets/*`, `screens/*`
- `assets/fonts/Lexend-*.ttf`

**Deferred:** Vision test, profiles, OpenCV pipelines, camera/lens behavior, simulation view, system-wide filter.
