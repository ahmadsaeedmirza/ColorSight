# Architecture

## Tech stack (and why)

| Choice | Role | Why |
|--------|------|-----|
| **Python 3** | App language | Course/project fit; strong NumPy/OpenCV ecosystem for color vision work |
| **Kivy** | UI framework | Cross-platform (desktop + Android via Buildozer); flexible canvas for custom pastel UI |
| **KivyMD** | *Not used (Phase 0)* | Material defaults fight the pastel notes look; pure Kivy + custom widgets is cleaner |
| **Material Icons TTF** | UI icons | Lexend has no icon glyphs; ligature font keeps icons vector-sharp and consistent |
| **NumPy** | Array math | Fast color transforms, matrix ops for correction profiles (Phase 1) |
| **OpenCV** | Image / camera | Capture, resize, color-space conversion, live frame pipelines |
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
└── colorsight/
    ├── app.py              # ColorSightApp + RootShell (SM + FloatingNavBar)
    ├── theme/
    │   ├── tokens.py       # Colors, Radii, Spacing, Fonts, Icons
    │   ├── theme.py        # register_fonts() — Lexend + Material Icons
    │   └── geometry.py     # clamp_radius / clamped_radii
    ├── widgets/
    │   ├── icon.py         # Icon helper (Material ligatures)
    │   ├── rounded_card.py
    │   ├── pastel_card.py
    │   ├── chip.py
    │   ├── pill_search_bar.py
    │   ├── floating_nav_bar.py
    │   └── primary_button.py
    └── screens/
        ├── welcome.py
        ├── home.py
        ├── _placeholder.py
        └── test / photos / camera / lens / profile / settings
```

## Modules (current)

- **`colorsight.app`** — `RootShell` hosts `ScreenManager` + floating nav (hidden on `welcome`); nav width = screen − 2×`nav_margin`.
- **`colorsight.theme`** — Tokens, font/icon registration, geometry clamping.
- **`colorsight.widgets`** — Design-system components including `Icon`.
- **`colorsight.screens`** — Shell screens; nav-visible screens use ScrollView + `Spacing.nav_clearance` bottom padding.

## Data flow (Phase 0 shell)

```
main.py
  └─ ColorSightApp.build()
       ├─ register_fonts()  # Lexend + Material Icons
       ├─ ScreenManager
       │    ├─ welcome → home (CTA)
       │    ├─ home ↔ test / photos / camera / lens / profile / settings
       │    └─ FloatingNavBar switches named screens
       └─ (Phase 1 later) correction profile → image/camera pipelines
```

## Design decisions

1. **Pure Kivy over KivyMD** for pastel cards + floating pill nav.
2. **Material Icons font** (not emoji / Lexend) for all chrome icons.
3. **Clamp every canvas radius** with `min(r, w/2, h/2)` so pills are capsules.
4. **Tokens in Python** (`tokens.py`) shared by widgets and docs.
5. **Stable screen ids** for nav and future deep-links.
6. **Desktop-first** — `python main.py` before Buildozer cycles.
