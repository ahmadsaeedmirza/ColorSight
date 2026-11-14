# Architecture

## Tech stack (and why)

| Choice | Role | Why |
|--------|------|-----|
| **Python 3** | App language | Course/project fit; NumPy/OpenCV ecosystem |
| **Kivy** | UI | Desktop + Android via Buildozer; custom pastel UI |
| **NumPy / OpenCV / Pillow** | Color + stimuli | CVD math; CIE u'v'; Landolt C / legacy plates |
| **Buildozer** | Android packaging | Kivy → APK |

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
    ├── photo_io.py         # Desktop chooser; Android Photo Picker + MediaStore
    └── screens/
        ├── photos.py / photo_widgets.py   # Photos correction UI
        └── test_screen.py / test_widgets.py
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
- Display size ≈ **190 dp** (~30 mm).
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
| Pick | Desktop: tkinter jpg/png/webp. Android 13+: Photo Picker (`PICK_IMAGES`); older: `GET_CONTENT` + optional `READ_MEDIA_IMAGES` / `READ_EXTERNAL_STORAGE`. |
| Preview | Longest side ≤ **1080**; bg thread + shimmer; ~100 ms Strength debounce; cache Corrected/Simulation for instant mode toggle. |
| Modes | Default **Corrected** (whole image filtered). Divider starts at **0%** (handle at left); drag right to reveal original. Reset to 0% on Corrected↔Simulation and new pick. Original = no divider. |
| Strength | Reloaded from disk on every Photos enter; percent-rounded. Preview-only. |
| Save / Share | Full-res for **current mode** + current Strength. MediaStore + FileProvider / desktop fallback. |
| Comparison | `build_comparison_card` — “Normal vision” \| “How I see it”, ≤2048. |

## Camera + Lens (shared live pipeline)

| Piece | Role |
|-------|------|
| `camera_source.py` | Desktop OpenCV webcam; `FakeFrameSource` for smoke; Android Camera4Kivy hook + runtime CAMERA permission |
| `camera_pipeline.py` | BGR↔RGB, live downscale (~560), loupe median/zoom crop, `LabelSmoother`, `name_loupe_color` → `core.name_color` |
| `screens/camera.py` | Full-bleed preview; mode pill; Strength; freeze/capture; loupe toggle; flip (Android) |
| `screens/lens.py` | Redirects to Camera with loupe enabled (no duplicated pipeline) |
| `screens/camera_widgets.py` | `LivePreviewStage`, `LoupeOverlay`, `CameraModeToolbar` |

Frame loop: latest-frame drop (no queue) → bg thread process → single texture blit. Start on enter / stop on leave; app pause/resume. Default Corrected + Strength from saved profile when present.

Helpers/widgets also: Photos `BeforeAfterViewer`, `PhotoModeToolbar`, `PreviewSeverityBar`, `TextLinkButton`, `LoadingShimmer`. Callbacks use `*_cb` names only.

## UI notes

- Test flow: **checklist → Trivector trials (D-pad + can't see, 6 s timeout) → hue arrange → results**.
- Photos: disk profile reload → pick → Corrected @ split 0% → Strength / save-share.
- Camera/Lens: shared live correction + loupe (`name_color`); Settings toggles FPS overlay.
- `FloatingNavBar`: five identical slots; blue `+` FAB clamped inside pill.
- Never name custom widgets after built-in Kivy widgets; `Icon` uses **`icon_size`**.
