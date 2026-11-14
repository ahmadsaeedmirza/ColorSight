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
- **Photos** must reuse `core.apply_correction` / `apply_simulation` / `CorrectionProfile` — do not reimplement CVD math in the UI. Preview severity is temporary; never overwrite the saved profile from Photos. Never show file paths in pick/save UI.
- **Photos Android I/O:** prefer Photo Picker + MediaStore (no broad storage on 13+ / no `WRITE_EXTERNAL_STORAGE` on 10+). Keep `tests/test_image_pipeline.py` green when touching pipeline helpers.
- Desktop-first during development: `python main.py` must keep working; `python -m unittest discover -s tests` must stay green when touching `/core`.
- Do not implement Phase 2 (system-wide color filter / Shizuku) until Phase 1 is complete and explicitly requested.
- **Never name custom widgets after built-in Kivy widgets** (`ProgressBar`, `Button`, `Label`, `Slider`, `Image`, `Switch`, …). Kivy binds `style.kv` by class name and will crash or mis-style collisions. Use prefixed names (e.g. `PillProgressBar`, `PreviewSeverityBar`).
- **Kivy callback props:** do **not** name an `ObjectProperty` `on_<name>` when the same widget also has a Kivy property `<name>` (e.g. `mode` + `on_mode`). Kivy will call that attribute on change and crash if it is `None`. Use `mode_cb` / `save_cb` / `split_cb` / `change_cb`, and always `if callable(cb)` before invoke.
- **Icons:** use `colorsight.widgets.Icon` + Material Icons ligatures — never Lexend/emoji for chrome icons. Glyph size = **`icon_size=`** (default 24); never pass Kivy widget `size=` a single number.
- **PastelCard** long copy: use `auto_height=True` so wrapped subtitles are not clipped.
- **Radii:** always clamp with `clamp_radius` / `clamped_radii` (`min(r, w/2, h/2)`) on fills and shadows.
- **Nav screens:** ScrollView (or equivalent) + `Spacing.nav_clearance` bottom padding so content is not hidden behind the floating nav.

## Scope discipline

- Implement only what the current prompt asks for.
- When the prompt says “do NOT build features yet,” ship shell, docs, and design only.
