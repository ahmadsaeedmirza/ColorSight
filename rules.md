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
- **Plate quality:** keep `tests/test_plate_validation.py` green (ΔE / ΔL* / figure count / stroke / IoU). Regenerate or tune palettes when gates fail; use `tools/preview_plates.py` to inspect.
- **Vision Test results** must keep a clear screening disclaimer (not a medical diagnosis; display variation). After save, show friendly copy only — never surface filesystem paths in the UI.
- Desktop-first during development: `python main.py` must keep working; `python -m unittest discover -s tests` must stay green when touching `/core`.
- Do not implement Phase 2 (system-wide color filter / Shizuku) until Phase 1 is complete and explicitly requested.
- **Never name custom widgets after built-in Kivy widgets** (`ProgressBar`, `Button`, `Label`, `Slider`, `Image`, `Switch`, …). Kivy binds `style.kv` by class name and will crash or mis-style collisions. Use prefixed names (e.g. `PillProgressBar`).
- **Icons:** use `colorsight.widgets.Icon` + Material Icons ligatures — never Lexend/emoji for chrome icons.
- **Radii:** always clamp with `clamp_radius` / `clamped_radii` (`min(r, w/2, h/2)`) on fills and shadows.
- **Nav screens:** ScrollView (or equivalent) + `Spacing.nav_clearance` bottom padding so content is not hidden behind the floating nav.

## Scope discipline

- Implement only what the current prompt asks for.
- When the prompt says “do NOT build features yet,” ship shell, docs, and design only.
