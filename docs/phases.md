# Phases

## Phase 0 — Setup, docs, design system, app shell

- Project rules + `/docs` living documentation
- Design tokens and reusable widgets matching pastel notes-app reference
- ScreenManager shell: Welcome, Home, and placeholders
- Desktop run via `python main.py`
- Buildozer scaffolding + production notes
- Shell polish: Material Icons, radius clamping, chip contrast, floating nav fit, ScrollView/`nav_clearance`

## Phase 1 — Color vision assist

### Engine foundation *(done — `/core`)*

- Machado CVD simulation (protanopia / deuteranopia / tritanopia, severity 0–1)
- Daltonization correction matrix + `CorrectionProfile` JSON
- Vectorized `apply_correction` / `apply_simulation`
- `name_color` for magnifier labeling
- Unit tests in `/tests`

### In-app UI features *(next)*

| Feature | Description |
|---------|-------------|
| Color vision test | Guided test to estimate deficiency type / severity |
| Correction profile UI | Create/edit/persist profile via `CorrectionProfile` |
| Image correction | Apply profile to user-selected photos |
| Live camera correction | Apply profile to the live camera feed |
| Magnifier lens | Loupe overlay that **names** the color under the sample point (`name_color`) |
| Simulation view | Preview how scenes appear under simulated deficiency / correction |

Stack: NumPy + OpenCV in `core/`, Kivy UI in `colorsight/`, packaged with Buildozer.

## Phase 2 — System-wide filter *(parked / later)*

- Android **system-wide** custom color filter
- Approach: **4×4 SurfaceFlinger color matrix**
- Privileged / elevated path via **Shizuku** (not a normal Play-store permission model)
- Explicitly out of scope until Phase 1 UI is done and this phase is requested

Do not implement Phase 2 scaffolding beyond documenting it here.
