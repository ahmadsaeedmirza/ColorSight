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
├── core/
│   ├── trivector.py   # LIVE Vision Test — CCT Trivector (u'v' staircases)
│   ├── plates.py      # LEGACY Ishihara-style plates (kept + tested, not in UI flow)
│   ├── scoring.py     # Legacy plate scoring + hue_arrangement_error
│   ├── machado.py / engine.py / profile.py / naming.py
├── tests/             # Engine + trivector + legacy plate gates
├── tools/             # preview_plates.py, flow_trivector.py
├── debug/             # gitignored preview output
└── colorsight/        # Kivy UI (test_screen Trivector flow, …)
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

## UI notes

- Test flow: **checklist → Trivector trials (arrows + can't see, 6 s timeout) → hue arrange → results**.
- Results: type, severity label + 0–100 bar, per-axis pastel bars, before/after swatches, disclaimer, Save (friendly copy only).
- `FloatingNavBar`: five identical slots; blue `+` FAB clamped inside pill.
- Never name custom widgets after built-in Kivy widgets (`PillProgressBar`, `ArrowPad`, …).
