# ColorSight

Assistive color-vision toolkit for Android and desktop. Take a short **Cambridge Colour Test–style Trivector** screening, then correct gallery photos and live camera frames for your eyes — and name colors under a magnifier loupe.

> **Screening tool, not a medical diagnosis.** Results vary with display brightness, night mode, and blue-light filters. See Settings → Display tips.

## Features (Phase 1)

| Feature | What it does |
|---------|----------------|
| **Vision Test** | Trivector staircases + hue arrange → type & severity → saved `CorrectionProfile` |
| **Photos** | Gallery pick, Corrected/Simulation/Original, Strength preview, save/share, comparison card |
| **Camera** | Live correction (OpenCV on desktop; Camera4Kivy on Android), freeze/capture |
| **Lens** | Same live pipeline with a loupe + `name_color` |
| **Profile** | View result, fine-tune severity (only place that overwrites the saved profile), clear |
| **Settings** | About, privacy, display tips, FPS debug toggle |

## Run on desktop

```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Tests and smoke scripts:

```bash
python -m unittest discover -s tests -q
python tools/flow_trivector.py
python tools/flow_photos.py
python tools/smoke_photos_ui.py
# Fake camera (no webcam):
# PowerShell: $env:COLORSIGHT_FAKE_CAMERA=1
python tools/smoke_camera_ui.py
```

## Build the Android APK

Native Windows Buildozer is not recommended. Use **WSL2 Ubuntu** and follow the step-by-step guide in [`docs/production.md`](docs/production.md).

Short path on Linux/WSL:

```bash
chmod +x tools/build_android.sh
./tools/build_android.sh          # → dist/colorsight-*-debug.apk
adb install -r dist/colorsight-*-debug.apk
```

## Limitations

- Not a clinical diagnosis; screens differ.
- Camera FPS, Photo Picker, MediaStore, and FileProvider share need **on-device** verification (checklist in `docs/production.md`).
- Phase 2 (system-wide Android color matrix via Shizuku) is **not** implemented.

## Docs

Living docs in `/docs`: `architecture.md`, `design.md`, `production.md`, `phases.md`, `memory.md`. Project rules in `rules.md`.
