# Architecture

## Tech stack (and why)

| Choice | Role | Why |
|--------|------|-----|
| **Python 3** | App language | Course/project fit; NumPy/OpenCV ecosystem |
| **Kivy** | UI | Desktop + Android via Buildozer; custom pastel UI |
| **NumPy / OpenCV / Pillow** | Color + plates | Vectorized CVD math; Lab/HSV; Lexend digit masks |
| **Buildozer** | Android packaging | Kivy → APK |

## Folder structure

```
ColorSight/
├── core/
│   ├── plates.py      # Procedural plates + metadata + metrics
│   ├── scoring.py     # expected-answer classification (+ inconclusive)
│   ├── machado.py / engine.py / profile.py / naming.py
├── tests/             # Engine + plate validation + respondent sims
├── tools/preview_plates.py  # debug/plates views + contact_sheet + figure_only
├── debug/             # gitignored preview output
└── colorsight/        # Kivy UI (test_screen, FloatingNavBar, …)
```


## Vision-test plates (`core/plates.py`)

**Original procedural artwork** — not copyrighted Ishihara images.

Pipeline per plate:

1. **Bold digit mask** — Lexend-SemiBold (Bold fallback) at ~60% of plate diameter, **no dilate**; light erode so counters of 3/6/8/9 stay open. Stroke targets ~3–4 average-dot diameters.
2. **Dense hex packing** — small radii capped vs stroke (~stroke/7), light air gap (no heavy overlap/blobbing).
3. **Figure vs ground** — centers tested against an **inset** copy of the ink mask so painted disks cannot spill into counters; `RenderedPlate.mask` stores the full ink for metrics.
4. **Confusion-line palettes** — equiluminant figure/ground bases (ΔL* < 3) with high normal ΔE; under the matching Machado simulation @ severity 1.0, ΔE ≤ 6 on hidden/classify/tritan plates. Small a*/b* jitter only (no brightness cue). Palettes/ΔE gates are independent of shape tuning.

### Battery metadata (`DEFAULT_BATTERY`, 14 plates)

| Role | Count | Expected answers |
|------|-------|------------------|
| Control | 1 | Everyone sees the digit |
| Hidden RG | 6 | Normal (+ tritan) see digit; protan & deutan → can't see |
| Classify protan | 2 | Normal/deutan/tritan see; protan → can't see |
| Classify deutan | 3 | Normal/protan/tritan see; deutan → can't see |
| Tritan | 2 | Normal/protan/deutan see; tritan → can't see |

Each `PlateSpec` stores `expected_normal / expected_protan / expected_deutan / expected_tritan` (`None` = "can't see").

`RenderedPlate` carries `image`, `mask`, and `dots` for validation and UI.

### Automated plate gates

**Color / geometry** (`tests/test_plate_validation.py`) — every plate, fail with plate id:

| Gate | Threshold |
|------|-----------|
| Figure dot count | ≥ 40 |
| Stroke width | ≥ 3 average-dot diameters |
| Normal mean Lab ΔE (figure vs ground) | ≥ 20 |
| Matching CVD ΔE @ severity 1.0 (hidden/classify/tritan) | ≤ 6 |
| Mean ΔL* | < 3 |
| IoU (gap-filled figure dots vs digit mask) | ≥ 0.7 |

**Shape recognizability** (`tests/test_plate_recognizability.py`) — color-independent:

| Gate | Rule |
|------|------|
| Template match | Rasterize figure dots → binary; best IoU/corr vs clean Lexend 0–9 equals `expected_normal` |
| Margin | Best score − runner-up ≥ `RECOG_MARGIN` (0.08) |
| Topology | Hole count via `cv2.findContours` hierarchy matches digit (8→2, 6/9/0/4→1, 3/7/…→0) |

Preview: `python tools/preview_plates.py` → per-view PNGs, `{id}_figure_only.png`, and `debug/plates/contact_sheet.png` (gitignored).

## Scoring (`core/scoring.py`)

Match each response against the per-viewer expected table (`None` ↔ "can't see").

**Thresholds:**

| Constant | Value | Meaning |
|----------|-------|---------|
| `MATCH_RATE_CLEAR` | 0.75 | Winning type must match ≥ this fraction |
| `LEAD_MARGIN` | 0.12 | Must beat #2 by this margin |
| `NORMAL_MIN_MATCH` | 0.85 | Normal needs a high match rate |
| `CONTROL_FAIL_INCONCLUSIVE` | 0.5 | Failing control → often inconclusive |

Outcomes: `normal` | `protanopia` | `deuteranopia` | `tritanopia` | **`inconclusive`**.

Severity blends miss-vs-normal rate with hue-arrangement error. Screening only — not a medical diagnosis.

Respondent unit tests: `simulate_respondent(type)` → `score_screening` asserts the matching class.

## Color math (CVD engine)

Simulation: \(\mathbf{rgb}_{sim} = S(\textit{type}, s)\,\mathbf{rgb}\) (Machado 2009).  
Daltonization: \(C = I + E(I - S)\).  
Naming: Lab nearest swatch + HSV neutrals.

## UI notes

- Test flow: intro → 14 plates → hue arrange → results (disclaimer + save).
- Save copy: “Your color profile has been saved” (path only in logs).
- `FloatingNavBar`: five identical icon+label slots; blue `+` FAB centered on Camera, clamped inside the pill.
- Never name custom widgets after built-in Kivy widgets (`PillProgressBar`, not `ProgressBar`).
