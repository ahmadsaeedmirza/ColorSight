# Memory log

Newest entries first. Append after every prompt per `rules.md`.

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
