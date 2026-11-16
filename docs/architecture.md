# Architecture

## Tech stack (and why)

| Choice | Role | Why |
|--------|------|-----|
| **Python 3** | App language | Course/project fit; NumPy/OpenCV ecosystem |
| **Kivy** | UI | Desktop + Android via Buildozer; custom pastel UI |
| **NumPy / OpenCV / Pillow** | Color + stimuli | CVD math; CIE u'v'; Landolt C / legacy plates |
| **Buildozer** / **p4a** / **GHA** | Android packaging | Preferred: GitHub Actions. **`preflight` job** (`tools/preflight.py` + non-GUI tests) before build. p4a **2026.05.09** → Python **3.14**, NDK **28c**, **arm64-v8a**, **`android.api=35`**; `PIP_CONSTRAINT`; wipe `build/venv` (never cache it); file-based packaging greps; `.gitattributes` LF (see `production.md`) |
| **Theme + insets + logging** | UI chrome | `ThemeController` + full `rebuild_ui`; `safe_area` → `Spacing.safe_*`; `NEUTRAL_BG` for test/tutorial/previews; rotating log |

## Folder structure

```
ColorSight/
├── core/                # CVD math only (do not change for Photos UI)
│   ├── trivector.py / plates.py / scoring.py
│   ├── machado.py / engine.py / profile.py / naming.py
├── tests/               # Engine + trivector + plates + image_pipeline
├── tools/               # flow_trivector.py, flow_photos.py, smoke_photos_ui.py
└── colorsight/
    ├── image_pipeline.py   # EXIF load, resize≤1080, before/after split, encode
    ├── photo_io.py         # Desktop chooser; androidstorage4kivy Chooser + SharedStorage (+ legacy fallback)
    ├── camera_source.py    # OpenCV / FakeFrameSource / AndroidCameraSource (Camera4Kivy)
    ├── camera_gpu.py       # Live preview fragment-shader mat3 (≡ core._apply_matrix)
    ├── exception_guard.py  # Kivy ExceptionHandler → log + PASS
    ├── logging_setup.py    # Rotating diagnostics log (Settings → View recent log)
    └── screens/
        ├── photos.py / photo_widgets.py   # Photos correction UI
        ├── camera.py / camera_widgets.py / lens.py
        └── test_screen.py / test_widgets.py
assets/android/
    ├── file_paths.xml              # FileProvider cache-path (ColorSightShare/)
    ├── fileprovider_snippet.xml    # <provider> XML for manifest merge
    ├── p4a_fileprovider_hook.py    # FileProvider inject helper
    └── p4a_hook.py                 # Chains CameraX gradle_options + FileProvider
camerax_provider/                   # Vendored CameraX Java + gradle_options (Camera4Kivy)
```

## Live Vision Test — Cambridge Colour Test Trivector (`core/trivector.py`)

Measures **type and severity** with interleaved 4-AFC staircases on three confusion axes in CIE 1976 **u'v'**.

### Color space

| Symbol | Value |
|--------|-------|
| Background (D65) | u'≈0.1978, v'≈0.4683, Y=0.45 |
| Protan copunctal | (0.6579, 0.5013) |
| Deutan copunctal | (−1.2174, 0.7826) |
| Tritan copunctal | (0.2573, 0.0) |

Target chromaticity = background moved toward the axis copunctal by distance **d** (Δu'v'). Convert u'v'+Y → XYZ → linear sRGB → gamma sRGB. **d** is clamped to the max in-gamut distance per axis (`max_in_gamut_d`).

### Stimulus

- Dot field via `pack_circles_dense` (shared with plates).
- **Landolt C** of target chromaticity; gap ≈ 1/5 of outer diameter; orientation ∈ {up, down, left, right}.
- Display size ≈ **132 dp** on the trial screen (texture still 512 px, linear-filtered).
- Per-dot luminance jitter from the **same** distribution for target and background (no luminance cue).

### Staircase (published CCT style)

- 4-AFC; **step doubles after error**, **halves after correct**; “can't see” = error.
- Three axes **interleaved** (random open axis each trial).
- Modes: **phone** — 8 reversals / mean of last 4; **full** — 11 / last 6.
- ~24–40 trials on phone mode.

### Classification

Normal cutoffs (Δu'v'): protan ≤ 0.0100, deutan ≤ 0.0100, tritan ≤ 0.0150 (plus clear lift vs calibrated normal baseline).

| Pattern | Result |
|---------|--------|
| No elevated axes | `normal` |
| Only / dominant tritan | `tritanopia` |
| Elevated protan or deutan | RG type by relative elevation (near-tie → `inconclusive`) |

Severity 0–1 from elevated-axis threshold via monotone **calibration curves** (Machado model observer). Hue-arrangement error **nudges** severity up lightly (does not dilute trivector). Labels: none / mild / moderate / strong.

`TrivectorResult.to_profile()` → `CorrectionProfile` (engine math unchanged).

### Model-observer calibration (`build_calibration`)

Observer sees mean target vs background through `apply_simulation` (Machado). Answers correctly when simulated Δu'v' > JND (with light noise). Binary-search thr(severity) per axis → install knots. Tests in `tests/test_trivector.py` cover gamut, luminance match, staircase convergence, type/severity accuracy (±0.15), monotonicity, mild cases.

## Legacy plates (`core/plates.py`) — not in UI flow

Procedural Ishihara-style battery kept for regression (`tests/test_plate_*`, `tests/test_plates_scoring.py`). Live Test screen no longer calls `generate_battery`.

## Scoring helpers

- **Live:** `score_trivector(session, hue_order=…)` in `trivector.py`.
- **Legacy:** `score_screening` / `simulate_respondent` in `scoring.py` (plate expected-answer tables).
- Shared: `hue_arrangement_error`.

## Color math (CVD engine) — unchanged

Simulation: \(\mathbf{rgb}_{sim} = S(\textit{type}, s)\,\mathbf{rgb}\) (Machado 2009).  
Daltonization: \(C = I + E(I - S)\).  
Naming: Lab nearest swatch + HSV neutrals.

## Photos — image correction (UI layer)

Reuses **`core.apply_correction`**, **`core.apply_simulation`**, and **`CorrectionProfile`** unchanged.

| Step | Behavior |
|------|----------|
| Profile gate | Load via `storage.profile_path()` / `app.correction_profile`. No profile → pink CTA card → Test. |
| Pick | Desktop: tkinter jpg/png/webp (unchanged). Android: prefer **`androidstorage4kivy.Chooser`** (`choose_content('image/*')`) → `SharedStorage.copy_from_shared` into app-private cache → existing EXIF/resize pipeline. Automatic fallback: legacy pyjnius Photo Picker (`ACTION_PICK_IMAGES`) / `GET_CONTENT` + URI→cache. Tap always shows “Opening gallery…” and logs every step (`photos: …`) to the diagnostics log. Settings → Debug → **Test photo picker**. |
| Preview | Longest side ≤ **1080**; bg thread + shimmer; ~100 ms Strength debounce; cache Corrected/Simulation for instant mode toggle. |
| Modes | Default **Corrected** (whole image filtered). Divider starts at **0%** (handle at left); drag right to reveal original. Reset to 0% on Corrected↔Simulation and new pick. Original = no divider. |
| Strength | Reloaded from disk on every Photos enter; percent-rounded. Preview-only. |
| Save / Share | Full-res for **current mode** + current Strength. Android: prefer `SharedStorage.copy_to_shared` into Pictures (album **ColorSight**); MediaStore insert remains the fallback → “Saved to your gallery”. Share: FileProvider `content://` + `FLAG_GRANT_READ_URI_PERMISSION` (`org.colorsight.colorsight.fileprovider`). Desktop share → save fallback. |
| Comparison | `build_comparison_card` — “Normal vision” \| “How I see it”, ≤2048. |

## Camera + Lens (shared live pipeline)

### Decision: Camera4Kivy + CameraX (not silent fake)

| Choice | Why |
|--------|-----|
| **Primary: Camera4Kivy + vendored `camerax_provider/`** | Official Android path for Kivy; ImageAnalysis pixels → our pipeline. Works with p4a **2026.05.09** / Python **3.14** / **arm64-v8a** / `android.api=35` when the provider hook + AndroidX deps are present. |
| **Not used: silent `FakeFrameSource` on Android** | Was the bug (color-bar “camera”). Android now shows a clear error card (permission / no camera / start failed) + Retry / Open settings. |
| **Desktop fallback only** | OpenCV webcam; if open fails → labeled **Test pattern** synthetic frames (never mistaken for a camera). |
| **Alternatives if Camera4Kivy breaks** | (1) Kivy built-in `Camera` Android provider, (2) thin pyjnius CameraX/Camera2 `ImageReader` bridge — only if Camera4Kivy cannot build; document any switch here. |

| Piece | Role |
|-------|------|
| `camera_source.py` | `OpenCVWebcamSource`; `FakeFrameSource` (desktop/smoke); `AndroidCameraSource` (Camera4Kivy `Preview` + `analyze_pixels_callback` @ ~640 long side); `CameraSessionState`; runtime CAMERA permission |
| `camera_pipeline.py` | BGR↔RGB, live downscale (**640** longest; try 480 if a device still stutters), loupe median/zoom crop, `LabelSmoother`, `name_loupe_color` → `core.name_color` (always on **original** frame, ~5 Hz) |
| `camera_gpu.py` | Fragment-shader `mat3` (identity / correction / simulation) matching `core.engine._apply_matrix` gamma clamp; `mat3_uniform` column-major |
| `screens/camera.py` | Full-bleed GPU `LivePreviewStage`; mode / Strength = matrix uniform only; freeze / capture / loupe / flip; timing+FPS debug line |
| `screens/lens.py` | Placeholder only — **Lens is a Camera loupe state** via `RootShell._navigate("lens")` + `Clock.schedule_once` → `set_loupe_enabled` (never flips `sm.current` from `on_pre_enter`) |
| `screens/camera_widgets.py` | `LivePreviewStage` (reused RGBA texture + `RenderContext` FS), `LoupeOverlay`, `CameraModeToolbar` |
| `exception_guard.py` | Global Kivy `ExceptionHandler` → diagnostics log + “Something went wrong”; `ExceptionManager.PASS` |
| `camerax_provider/` | Vendored CameraX Java + `gradle_options.py` (chained from `assets/android/p4a_hook.py`) |

Frame loop: after permission, attach a **full-size opacity-0** Camera4Kivy `Preview` behind `LivePreviewStage` (CameraX needs a real surface — a 2×2 preview yields a black feed), then `connect_camera` on the **next Clock frame** (Camera4Kivy Android rule: after `App.on_start`). Analyze pixels → latest-frame-wins → downscale → **upload raw** into one reused RGBA texture → GPU `mat3` draw. Strength/mode only update the uniform. Loupe crops the CPU original when on; color name ~5 Hz. Capture still uses CPU `render_mode_rgb` once. If no frame arrives within ~2.5 s on Android → error card. Timing (`recv` / `upload` / `draw` ms + fps) every 5 s to the log. `disconnect_camera` on leave/pause.

Helpers/widgets also: Photos `BeforeAfterViewer`, `PhotoModeToolbar`, `PreviewSeverityBar`, `TextLinkButton`, `LoadingShimmer`. Callbacks use `*_cb` names only.

## Profile + Settings

- **Profile:** reload from disk on enter; pastel hero (plain-language type, severity label + N/100, measured date); optional `AxisBars` when `thresholds` stored; before/after swatch strip; Retake / Fine-tune (confirm before overwrite; Reset to test result) / Clear (confirm). Optional JSON fields on `CorrectionProfile` (`measured_at`, `label`, `thresholds`, `test_severity`) — UI metadata only.
- **Settings:** About (version + screening note), Privacy (on-device only), Display tips, Debug FPS toggle (`_FpsToggle`, not Kivy `Switch`), **Test photo picker**, View recent log.

## App shell

- First run → Welcome (CTA to Test); later → Home (`colorsight.prefs`).
- Android/Escape back → Home from feature screens (`RootShell.go_back`).
- Home: chips filter + navigate; avatar → Profile; menu → Settings; search bar removed.

### Startup stages (crash-proof)

`ColorSightApp.build()` breadcrumbs (flushed) in order: logging → exception handler → fonts (+ usable probe) → safe_area → prefs/theme → profile → RootShell **essential screens** (welcome/home/settings) → `on_start` first-frame layout probe → deferred heavy screens (test/photos/camera/lens/profile) → 3 s watchdog.

**Why splash → black was happening:** p4a dismisses the splash as soon as Python is alive; the old shell then set a dark `Window.clearcolor` and blocked on importing **all** screens (including `core`→OpenCV and Camera) before any widget was shown — so the GL surface stayed an empty dark frame. Fix: cream clearcolor until first paint, keep Android `loadingscreen` until layout is sane, build essential screens first, import heavy modules via `importlib` per screen (package `__init__` is lazy), force ScreenManager/current screen to `Window.size`, treat a stuck 100×100 screen as broken.

| Stage | On failure |
|-------|------------|
| Fonts | If TTF missing / register / Label probe fails → **Roboto** names (never leave Labels on unregistered Lexend*) |
| safe_area / pyjnius | Defaults top **28 dp**, bottom **16 dp**; clamps top 0–80, bottom 0–48 |
| Theme / night mode / bad pref | **Light** tokens; clearcolor stays cream until first frame; then `apply_system_bars` paints Android status/nav bars to `Colors.bg` (no white chrome) |
| Camera GPU shader | Lazy compile on Camera enter; CPU `core` matrix path + status notice |
| androidstorage4kivy / Camera4Kivy | Lazy import inside the call site |
| Deferred screen import | That screen is skipped; nav/`ensure_screen` retries on demand |
| Any `build()` / `rebuild_ui()` exception | Plain **fallback error screen** (white/black, stock widgets): “ColorSight could not start”, exception + last 15 log lines, **Copy details** / **Reset app data** (prefs/theme only) / **Try again** |

`exception_guard` still returns `PASS` for non-fatal errors, shows a status line, counts faults in the first 5 s, and switches to the fallback if the root is empty / zero-size / tiny vs the window / invisible after 3 s.

## UI notes

- Test flow: **checklist → Trivector trials → hue → results**.
- Photos / Camera / Lens as above.
- `FloatingNavBar`: five identical slots; blue `+` FAB clamped inside pill; `navigate_cb`.
- `Chip` / `ChipRow`: auto-width single-line pills in a scrollbar-free horizontal `ScrollView`; `select_cb` / `change_cb`.
- `ScreenHeader`: shared back + gap + title (Photos, Camera, Settings, Profile, Test).
- `ArrowPad`: keyboard inverted-T; desktop `Window.on_key_down` arrows map to the same orient callbacks.
- Never name custom widgets after built-in Kivy widgets; `Icon` uses **`icon_size`**; callback props use `*_cb` + `callable()`.
- `RootShell` creates the nav **before** setting `sm.current` so first-run / Home switch cannot touch a missing nav.
