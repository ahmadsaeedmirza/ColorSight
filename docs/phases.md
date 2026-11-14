# Phases

## Phase 0 — Setup, docs, design system, app shell

- Project rules + `/docs` living documentation
- Design tokens and reusable widgets
- ScreenManager shell + Material Icons + radius clamping + nav clearance

## Phase 1 — Color vision assist

### Done

| Piece | Status |
|-------|--------|
| `/core` Machado simulation + daltonization + `CorrectionProfile` + `name_color` | Done |
| Unit tests for engine | Done |
| **Vision Test UI** — Trivector CCT (Landolt C) + hue arrange + results + save profile | Done |
| Test crash fix — `PillProgressBar` rename (no Kivy builtin name collision) | Done |
| Plate generator (legacy) — dense packing, confusion palettes, validation + recognizability tests | Done (kept, not in live flow) |
| Shape legibility — open counters, recognizability tests, contact sheet | Done |
| Trivector core — u'v' axes, staircase, model-observer calibration, accuracy tests | Done |
| ArrowPad Icon crash fix — use `icon_size`, not Kivy `size=` float | Done |
| Vision Test UI polish — D-pad, Question N, crisp stim blit, results labels/auto-height | Done |
| UI polish — result swatches, friendly save copy, nav slots + centered FAB | Done |
| **Photos / image correction** — profile gate, picker, before/after, modes, MediaStore save | Done |
| Photos toolbar crash fix — rename `on_mode`/`on_split` ObjectProperties to `*_cb` | Done |
| Photos Strength default/reset, divider labels, mode Save/Share, comparison card | Done |
| Photos default Corrected @ split 0% + disk profile reload | Done |
| **Camera** — live OpenCV/Camera4Kivy pipeline, modes, freeze/capture | Done |
| **Lens** — shared loupe + `name_color` (opens Camera with loupe on) | Done |
| Settings FPS debug toggle | Done |

### Remaining in-app features

| Feature | Description |
|---------|-------------|
| Correction profile UI | View/edit saved profile on Profile screen (“Update my profile”) |

Stack: NumPy + OpenCV in `core/`, Kivy UI in `colorsight/`, Buildozer packaging.

## Phase 2 — System-wide filter *(parked / later)*

- Android system-wide 4×4 SurfaceFlinger color matrix via Shizuku
- Out of scope until Phase 1 UI features above are done and this phase is requested
