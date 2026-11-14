# Architecture

## Tech stack (and why)

| Choice | Role | Why |
|--------|------|-----|
| **Python 3** | App language | Course/project fit; strong NumPy/OpenCV ecosystem for color vision work |
| **Kivy** | UI framework | Cross-platform (desktop + Android via Buildozer); flexible canvas for custom pastel UI |
| **KivyMD** | *Not used (Phase 0)* | Material defaults fight the pastel notes look; pure Kivy + custom widgets is cleaner |
| **NumPy** | Array math | Fast color transforms, matrix ops for correction profiles (Phase 1) |
| **OpenCV** | Image / camera | Capture, resize, color-space conversion, live frame pipelines |
| **Buildozer** | Android packaging | Standard Kivy → APK/AAB path; permissions and recipe management |

## Folder structure

```
ColorSight/
├── main.py                 # Entry point (desktop + Android)
├── requirements.txt
├── buildozer.spec          # Android packaging config
├── rules.md                # Mandatory docs + scope rules
├── docs/                   # Living documentation (always update)
│   ├── architecture.md
│   ├── production.md
│   ├── design.md
│   ├── phases.md
│   └── memory.md
├── assets/
│   └── fonts/              # Bundled Lexend TTFs
└── colorsight/
    ├── __init__.py
    ├── app.py              # ColorSightApp + ScreenManager wiring
    ├── theme/
    │   ├── tokens.py       # Design tokens (colors, radii, spacing, fonts)
    │   └── theme.py        # Font registration + KV helpers
    ├── widgets/            # Reusable UI components
    │   ├── rounded_card.py
    │   ├── pastel_card.py
    │   ├── chip.py
    │   ├── pill_search_bar.py
    │   ├── floating_nav_bar.py
    │   └── primary_button.py
    └── screens/            # ScreenManager screens (shell placeholders)
        ├── welcome.py
        ├── home.py
        ├── test_screen.py
        ├── photos.py
        ├── camera.py
        ├── lens.py
        ├── profile.py
        └── settings.py
```

## Modules (current)

- **`colorsight.app`** — Application class; builds `ScreenManager`, registers screens, owns root layout with floating nav.
- **`colorsight.theme`** — Single source of truth for visual tokens; registers Lexend with Kivy’s `LabelBase`.
- **`colorsight.widgets`** — Design-system components used by screens (cards, chips, nav, buttons).
- **`colorsight.screens`** — One module per screen; Phase 0 = layout + navigation only.

## Data flow (Phase 0 shell)

```
main.py
  └─ ColorSightApp.build()
       ├─ register_fonts()
       ├─ ScreenManager
       │    ├─ welcome → home (CTA)
       │    ├─ home ↔ test / photos / camera / lens / profile / settings
       │    └─ FloatingNavBar switches named screens
       └─ (Phase 1 later) correction profile → image/camera pipelines
```

No correction profiles, camera frames, or color naming yet — shell only.

## Planned Phase 1 data flow (not implemented)

```
Vision test results → CorrectionProfile (params)
        ↓
  Image picker / Camera feed / Magnifier sample
        ↓
  NumPy/OpenCV color transform
        ↓
  Display + optional simulation view + named color under lens
```

## Design decisions

1. **Pure Kivy over KivyMD** for Phase 0 so pastel cards, floating pill nav, and soft shadows match the reference notes-app look.
2. **Tokens in Python** (`tokens.py`) rather than only KV — easier to share between widgets and docs.
3. **Screen names are stable IDs** (`welcome`, `home`, `test`, …) so nav and future deep-links stay consistent.
4. **Desktop-first** — validate UI with `python main.py` before Buildozer cycles.
