# Architecture

## Tech stack (and why)

| Choice | Role | Why |
|--------|------|-----|
| **Python 3** | App language | Course/project fit; strong NumPy/OpenCV ecosystem for color vision work |
| **Kivy** | UI framework | Cross-platform (desktop + Android via Buildozer); flexible canvas for custom pastel UI |
| **KivyMD** | *Not used* | Material defaults fight the pastel notes look |
| **Material Icons TTF** | UI icons | Ligature font; Lexend has no icon glyphs |
| **NumPy** | Array math | Vectorized CVD transforms + plate buffers |
| **OpenCV** | Color spaces / drawing | Lab/HSV naming; digit masks + circle packing for plates |
| **Buildozer** | Android packaging | Kivy → APK path |

## Folder structure

```
ColorSight/
├── core/                   # Pure-Python color engine (no UI)
│   ├── machado.py / engine.py / profile.py / naming.py
│   ├── plates.py           # Procedural Ishihara-style plates (original)
│   └── scoring.py          # Screening classification + severity
├── tests/
├── colorsight/
│   ├── storage.py          # user_data_dir profile path
│   ├── screens/
│   │   ├── test_screen.py  # Vision test flow (intro→plates→hue→results)
│   │   └── test_widgets.py # PillProgressBar, Numpad, HueStrip
│   └── …
└── docs/
```

## Modules

### Color engine (`core`)

| Module | Responsibility |
|--------|----------------|
| `plates` | Procedural plates (circle packing + digit mask); `DEFAULT_BATTERY` (14); hue tile colors |
| `scoring` | `score_screening` → normal / protan / deutan / tritan + severity; `TestResult.to_profile()` |
| `engine` / `machado` / `profile` / `naming` | Simulation, daltonization, JSON profile, `name_color` |

**Copyright:** Plates are generated procedurally. We do **not** ship or copy patented/copyrighted Ishihara plate images.

### UI — Vision Test (`colorsight.screens.test_screen`)

Flow inside screen id `test`:

1. **Intro** — pastel cards + disclaimer + Start  
2. **Plates (14)** — one plate/screen, progress bar, large numpad, “Can't see anything”  
3. **Hue arrangement** — tap-to-swap colored tiles into rainbow order (severity cue)  
4. **Results** — type + severity, before/after simulation strip, Save profile, medical disclaimer  

Profile save: `CorrectionProfile` → `App.user_data_dir/correction_profile.json` via `colorsight.storage.profile_path()`.

## Data flow

```
Test UI answers + hue order
        ↓
score_screening() → TestResult (classification, severity)
        ↓
TestResult.to_profile() → CorrectionProfile
        ↓
profile.save(JSON)  +  apply_simulation for result demo
```

## Color math (brief)

### Simulation — Machado et al. 2009

\[
\mathbf{rgb}_{sim} = S(\textit{type},\, s)\, \mathbf{rgb}
\]

Severity \(s \in [0,1]\); tables step 0.1 with linear interpolation.

### Daltonization

\[
C = I + E(I - S),\quad \mathbf{rgb}_{out} = C\,\mathbf{rgb}\ \text{(clipped)}
\]

### Screening score (heuristic)

- Miss rates by plate axis (control / red–green / protan / deutan / blue–yellow)
- Hue permutation error normalized to \([0,1]\)
- Classification: normal vs protan vs deutan vs tritan; severity blends axis miss + hue error  
- **Screening only** — not a clinical diagnosis; display gamut varies by device

### Procedural plates

1. Build a soft digit mask (OpenCV font + slight rotation)  
2. Pack non-overlapping circles in a disk  
3. Color circles from figure vs ground palettes chosen for the plate’s confusion axis  

## Design decisions

1. `/core` stays UI-free; Test screen imports scoring/plates only.  
2. Original procedural plates avoid Ishihara copyright.  
3. Single digit answers keep the numpad simple on phones.  
4. Hue step adds a severity signal beyond binary plate misses.  
5. Explicit on-result disclaimer about screening limits and screen variation.
