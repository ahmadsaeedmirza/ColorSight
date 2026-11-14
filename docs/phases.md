# Phases

## Phase 0 — Setup, docs, design system, app shell *(current)*

- Project rules + `/docs` living documentation
- Design tokens and reusable widgets matching pastel notes-app reference
- ScreenManager shell: Welcome, Home, and placeholders
- Desktop run via `python main.py`
- Buildozer scaffolding + production notes (no feature pipelines yet)

## Phase 1 — Color vision assist (in-app)

| Feature | Description |
|---------|-------------|
| Color vision test | Guided test to estimate deficiency type / severity |
| Correction profile | Persist parameters derived from the test |
| Image correction | Apply profile to user-selected photos |
| Live camera correction | Apply profile to the live camera feed |
| Magnifier lens | Loupe overlay that **names** the color under the sample point |
| Simulation view | Preview how scenes appear under simulated deficiency / correction |

Stack for Phase 1: NumPy + OpenCV inside the Kivy app; still packaged with Buildozer.

## Phase 2 — System-wide filter *(parked / later)*

- Android **system-wide** custom color filter
- Approach: **4×4 SurfaceFlinger color matrix**
- Privileged / elevated path via **Shizuku** (not a normal Play-store permission model)
- Explicitly out of scope until Phase 1 is done and this phase is requested

Do not implement Phase 2 scaffolding beyond documenting it here.
