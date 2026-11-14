# Memory log

Newest entries first. Append after every prompt per `rules.md`.

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
