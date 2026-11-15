# ColorSight — Project Rules

## Mandatory documentation policy

**After EVERY prompt or code change, update the relevant files in `/docs`.**

This is not optional. Documentation is part of the deliverable, not an afterthought.

| File | Update when… |
|------|----------------|
| `docs/architecture.md` | Folder structure, modules, data flow, or tech-stack choices change |
| `docs/production.md` | Build steps, permissions, device testing notes, or known issues change |
| `docs/design.md` | Design tokens, components, screens, or visual language change |
| `docs/phases.md` | Phase scope, parked features, or roadmap items change |
| `docs/memory.md` | **Every** prompt — append a newest-first entry summarizing decisions and changes |

## How to log in `memory.md`

1. Put the newest entry at the **top** (below the title).
2. Include: date, short title, decisions made, files touched, and anything deferred.
3. Be specific enough that a future session can resume without re-deriving context.

## Code conventions

- Prefer pure **Kivy** for UI. Use **KivyMD** only when it clearly reduces custom work without fighting the pastel design system.
- Keep feature logic out of screen layout files when possible (separate modules under `colorsight/`).
- **Color math belongs in `/core`** (NumPy/OpenCV, no Kivy). UI screens import `core` — do not duplicate Machado/daltonize/naming/plates/scoring in widgets.
- **Ishihara-style plates must be procedural/original** — never ship or scrape copyrighted Ishihara plate images.
- **Live Vision Test** uses Cambridge Colour Test Trivector (`core/trivector.py`). Keep `tests/test_trivector.py` green (gamut, luminance match, staircase, type/severity calibration). Do not change correction-engine math when tuning the test.
- **Legacy plates** (`core/plates.py`) stay in-repo with `tests/test_plate_validation.py` + `tests/test_plate_recognizability.py` green, but are **not** used in the live Test UI flow.
- **Vision Test results** must keep a clear screening disclaimer (not a medical diagnosis; display variation). After save, show friendly copy only — never surface filesystem paths in the UI.
- **Photos** must reuse `core.apply_correction` / `apply_simulation` / `CorrectionProfile` — do not reimplement CVD math in the UI. Strength is temporary; never overwrite the saved profile from Photos. Never show file paths in pick/save/share UI.
- **Photos Android I/O:** Photo Picker (`ACTION_PICK_IMAGES` / `GET_CONTENT` fallback) via `startActivityForResult` + `android.activity.bind`; URI → app-cache; MediaStore save (`Pictures/ColorSight`); Share via FileProvider + `ACTION_SEND` + `FLAG_GRANT_READ_URI_PERMISSION` (`assets/android/` + `p4a.hook` + `production.md`). Never silent-fail pick/save/share — friendly UI + diagnostics log. Keep `tests/test_image_pipeline.py`, `tests/test_photos_pipeline.py`, and `tests/test_photo_io.py` green when touching Photos helpers.
- **Photos divider:** hide in Original; Corrected/Simulation = left original / right mode with labels; **default split 0%** (full filtered); handle hit ≥44 dp and fully inside image bounds. Reload profile from disk on every Photos/Camera enter.
- **Camera/Lens:** share one pipeline (`camera_source` + `camera_pipeline` + `camera_widgets`). Android = Camera4Kivy + vendored `camerax_provider` (never silent `FakeFrameSource`). Desktop may use labeled Test pattern only if the webcam fails. Drop frames instead of queueing; `connect_camera` / `disconnect_camera` on enter/leave/pause. Loupe samples **original** frames for `core.name_color`. Log every `camera_event` to the diagnostics log. Never auto-advance app state with orphan timers (user-driven only). Keep `tests/test_camera_pipeline.py` + `tests/test_camera_source.py` green.
- **Settings:** optional camera FPS overlay via `app.show_camera_fps` (not a Kivy `Switch` — use a custom toggle); when on, show real fps + frame size.
- Desktop-first during development: `python main.py` must keep working; `python -m unittest discover -s tests` must stay green when touching `/core`.
- **Android `buildozer.spec`:** single `version = …` line (no `version.regex` / `version.filename`). Keep requirements **unpinned** (`python3,kivy,numpy,opencv,pillow,pyjnius,android,camera4kivy,gestures4kivy`) for python-for-android **2026.05.09** / Python **3.14**. Do not reintroduce `kivy==2.3.0` / `numpy==1.26.4` / `pillow==10.4.0`. p4a **ignores** `requirements=` pins for pure-Python pip modules — pin `charset-normalizer==3.4.9` in repo-root **`constraints.txt`** and set **`PIP_CONSTRAINT`** in CI. Use **`android.ndk = 28c`** and **`android.archs = arm64-v8a`**. Desktop `requirements.txt` is separate.
- **Preferred APK build:** GitHub Actions (`.github/workflows/android.yml`) — `workflow_dispatch` or push to `build-apk`. Keep WSL Buildozer as fallback only. See `production.md` **Cloud build** + troubleshooting (FreeType, NDK, `PIP_CONSTRAINT`, corrupt `build/venv`, packaging-check `pipefail`). Always delete `.buildozer/android/platform/build-*/build/venv` before buildozer (CI + `tools/build_android.sh`); never cache that venv (`buildozer-v2-` key). Packaging checks must grep dump **files** (not `echo | grep` under `pipefail`). Upload the APK with `if: always()` when present. CI must fail if FileProvider, CAMERA permission, or CameraX provider classes are really missing.
- **FileProvider + CameraX packaging:** `p4a.hook` = `assets/android/p4a_hook.py` (chains CameraX `gradle_options` + FileProvider inject). Keep vendored `./camerax_provider`. `android.enable_androidx = True`; do not rely on unsupported buildozer keys alone.
- **Window size / density:** Set `Config` / `Window.size` **only on desktop** (`platform not in ('android','ios')`). Never lock Android to a phone-frame pixel size. Pre-build layout check: `python tools/run_phone_sim.py`. Use `dp`/`sp` + `size_hint`; bind to size — do not cache `Window.width` at import.
- **Theme:** Settings System/Light/Dark via `ThemeController`; apply = update tokens + **full in-process UI rebuild** (`rebuild_ui`), not a partial canvas walk. System follows Android night mode on start/resume. **Accuracy rule:** Vision Test (incl. tutorial), Photos/Camera preview hosts always use `NEUTRAL_BG`. Opaque BGs + `Window.clearcolor`.
- **Safe areas:** `Spacing.safe_top` / `safe_bottom` from `safe_area.refresh_safe_insets()`; apply to headers, Home, Welcome, and floating nav. Phone-sim debug insets via env / `set_debug_insets`.
- **Home chips:** reset `ChipRow.scroll_x` to 0 on enter and after theme rebuild (first chips must not start scrolled away).
- **Vision Test tutorial:** first Start test shows a skippable 3-step tip + optional practice (UI only — never feeds the staircase/scoring/profile). Pref `test_tutorial_seen`; Replay in Settings + checklist link.
- **Diagnostics:** rotating log in `user_data_dir` + Settings → View recent log (no paths in UI) + global `sys.excepthook`.
- **Debug APK installs:** each CI build has a new debug key — uninstall `org.colorsight.colorsight` before installing; Play Protect warnings on debug builds are expected.
- **Phase 1 is complete.** Do not implement Phase 2 (system-wide SurfaceFlinger 4×4 color matrix via Shizuku) until explicitly requested after the device checklist in `production.md`.
- **Profile fine-tune** is the only UI that overwrites the saved correction profile (always confirm). Photos/Camera Strength remain preview-only.
- **Never name custom widgets after built-in Kivy widgets** (`ProgressBar`, `Button`, `Label`, `Slider`, `Image`, `Switch`, …). Kivy binds `style.kv` by class name and will crash or mis-style collisions. Use prefixed names (e.g. `PillProgressBar`, `PreviewSeverityBar`).
- **Kivy callback props:** never name callback `ObjectProperty`s `on_<name>` (conflicts with Kivy’s property observers, even without a matching `<name>` prop). Use `*_cb` (`mode_cb`, `select_cb`, `change_cb`, `navigate_cb`, …) and always `if callable(cb)` before invoke.
- **Icons:** use `colorsight.widgets.Icon` + Material Icons ligatures — never Lexend/emoji for chrome icons. Glyph size = **`icon_size=`** (default 24); never pass Kivy widget `size=` a single number.
- **Chips / pill labels:** Home `Chip` must stay **single-line** and grow to the label (`text_size=(None,None)`; width = texture + ~18 dp pad/side). Put chip rows in a horizontal scrollbar-free `ScrollView` for narrow widths. Fixed-width toolbar segments use `shorten=True` + `max_lines=1` instead of wrapping.
- **ScreenHeader:** back control + `Spacing.header_gap` before the title; always include `Spacing.safe_top` so headers clear the status bar / notch.
- **Vision Test D-pad:** keyboard inverted-T (Up; Left·Down·Right); desktop arrow keys may answer; do not advance trials from other keys. Keep orient / can't-see mapping unchanged.
- **PastelCard** long copy: use `auto_height=True` so wrapped subtitles are not clipped.
- **Radii:** always clamp with `clamp_radius` / `clamped_radii` (`min(r, w/2, h/2)`) on fills and shadows.
- **Nav screens:** ScrollView (or equivalent) + `Spacing.nav_clearance` bottom padding so content is not hidden behind the floating nav (trial screen may use a tighter bottom inset that still clears the nav pill).
- **No orphan timers** that change app state by themselves; never show filesystem paths in the UI.

## Scope discipline

- Implement only what the current prompt asks for.
- When the prompt says “do NOT build features yet,” ship shell, docs, and design only.
