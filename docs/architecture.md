# Architecture

## Tech stack (and why)

| Choice | Role | Why |
|--------|------|-----|
| **Python 3** | App language | Course/project fit; strong NumPy/OpenCV ecosystem for color vision work |
| **Kivy** | UI framework | Cross-platform (desktop + Android via Buildozer); flexible canvas for custom pastel UI |
| **KivyMD** | *Not used (Phase 0)* | Material defaults fight the pastel notes look; pure Kivy + custom widgets is cleaner |
| **Material Icons TTF** | UI icons | Lexend has no icon glyphs; ligature font keeps icons vector-sharp and consistent |
| **NumPy** | Array math | Vectorized 3×3 CVD transforms for real-time frames |
| **OpenCV** | Color spaces / I/O | RGB↔Lab/HSV for naming; future camera/image pipelines |
| **Buildozer** | Android packaging | Standard Kivy → APK/AAB path; permissions and recipe management |

## Folder structure

```
ColorSight/
├── main.py
├── requirements.txt
├── buildozer.spec
├── rules.md
├── docs/
├── assets/
│   ├── fonts/              # Lexend TTFs + OFL
│   └── icons/              # MaterialIcons-Regular.ttf + Apache LICENSE
├── core/                   # Pure-Python color engine (no UI)
│   ├── cvd_types.py
│   ├── machado.py          # Machado 2009 matrices + severity interpolation
│   ├── engine.py           # simulate / daltonize / apply_*
│   ├── profile.py          # CorrectionProfile + JSON I/O
│   └── naming.py           # name_color (Lab nearest + HSV neutrals)
├── tests/                  # unittest suite for /core
└── colorsight/             # Kivy UI shell
    ├── app.py
    ├── theme/
    ├── widgets/
    └── screens/
```

## Modules

### UI (`colorsight`)

- **`colorsight.app`** — `RootShell` hosts `ScreenManager` + floating nav.
- **`colorsight.theme`** — Tokens, font/icon registration, geometry clamping.
- **`colorsight.widgets` / `screens`** — Shell UI only (no color math).

### Color engine (`core`) — Phase 1 foundation

| Module | Responsibility |
|--------|----------------|
| `cvd_types` | `CVDType`: protanopia, deuteranopia, tritanopia (+ aliases) |
| `machado` | Tabulated Machado et al. 2009 3×3 RGB matrices; interpolate severity |
| `engine` | `simulation_matrix`, `build_correction_matrix`, `apply_simulation`, `apply_correction` |
| `profile` | `CorrectionProfile(type, severity, matrix)` save/load JSON |
| `naming` | `name_color(rgb)` via Lab nearest-neighbor + HSV neutral handling |

Public import: `from core import CorrectionProfile, apply_correction, apply_simulation, name_color, CVDType`.

## Data flow

```
Vision test (UI, later) → type + severity
        ↓
CorrectionProfile.create() → C = I + E(I − S)
        ↓
JSON on disk  ←→  profile.save / load
        ↓
apply_correction(image, profile)   # photos / live camera
apply_simulation(image, type, sev) # simulation view
name_color(rgb)                    # magnifier lens label
```

## Color math (brief)

### Simulation — Machado et al. 2009

CVD appearance is a single linear map in RGB:

\[
\mathbf{rgb}_{sim} = S(\textit{type},\, s)\, \mathbf{rgb}
\]

- \(S\) is a 3×3 matrix from Machado’s published tables (severity \(s \in [0,1]\), step 0.1).
- \(s = 0\) → identity (normal vision); \(s = 1\) → dichromacy (protanopia / deuteranopia / tritanopia).
- Intermediate \(s\): linear interpolation between adjacent tabulated matrices.

### Daltonization / correction — Fidaner-style error shift

1. Simulate: \(\mathbf{rgb}_{sim} = S\,\mathbf{rgb}\)
2. Error (lost information): \(\mathbf{e} = \mathbf{rgb} - \mathbf{rgb}_{sim} = (I - S)\,\mathbf{rgb}\)
3. Redistribute with type-specific \(E\) into channels the user can still use:

\[
\mathbf{rgb}_{out} = \mathbf{rgb} + E\,\mathbf{e} = \bigl(I + E(I - S)\bigr)\mathbf{rgb}
\]

The composite correction matrix stored on the profile is:

\[
C = I + E(I - S)
\]

So real-time paths are one vectorized matmul per frame: `pixels @ C.T`, then clip to [0, 1] / uint8.

Error-shift \(E\) (rows = output R,G,B):

| Type | Idea |
|------|------|
| Protanopia | Push lost red into G and B |
| Deuteranopia | Push lost green into R and B |
| Tritanopia | Push lost blue into R and G |

### Color naming

1. Convert sample RGB → CIE Lab (OpenCV) and HSV.
2. Low saturation → black / gray / white by value.
3. Otherwise nearest named swatch by Euclidean Lab distance (small fixed palette: “dark red”, “light green”, “olive”, …).

### Performance

Transforms are fully vectorized NumPy (`reshape(-1,3) @ M.T`). No per-pixel Python loops. Unit tests include a soft 720p timing budget.

## Design decisions

1. **`core/` is UI-free** so math can be unit-tested and reused by future screens without Kivy.
2. **Machado tables** (not Brettel/Viénot alone) for unified anomalous-trichromacy severity.
3. **Composite \(C\)** stored on `CorrectionProfile` for fast apply + JSON portability.
4. **RGB order** in `core` APIs (convert BGR↔RGB at camera/OpenCV boundaries in UI later).
5. Pure Kivy UI; Material Icons; clamp canvas radii; desktop-first.
