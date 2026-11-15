# Phases

## Phase 0 — Setup, docs, design system, app shell

- Project rules + `/docs` living documentation
- Design tokens and reusable widgets
- ScreenManager shell + Material Icons + radius clamping + nav clearance

## Phase 1 — Color vision assist — **COMPLETE**

| Piece | Status |
|-------|--------|
| `/core` Machado simulation + daltonization + `CorrectionProfile` + `name_color` | Done |
| Unit tests for engine | Done |
| **Vision Test UI** — Trivector CCT + hue arrange + results + save profile | Done |
| **UI polish** — Chip auto-width/scroll, inverted-T D-pad + keyboard arrows, ScreenHeader gap/top inset | Done |
| Plate generator (legacy) — kept + tested, not in live UI | Done |
| Trivector core + calibration tests | Done |
| **Photos** — pick, Corrected@0% divider, Strength, save/share, comparison | Done |
| **Camera** — live OpenCV / Camera4Kivy pipeline, freeze/capture | Done |
| **Lens** — shared loupe + `name_color` | Done |
| **Profile** — hero card, swatches, fine-tune (only overwrite), clear | Done |
| **Settings** — About, Privacy, Display tips, FPS debug | Done |
| First-run Welcome → test; later launches → Home; Android back | Done |
| Buildozer.spec + icons/splash + WSL build guide + `tools/build_android.sh` | Done |
| Buildozer requirements unpinned for p4a 2026.05.09 / Python 3.14 | Done |
| Buildozer NDK 28c + arm64-v8a-only APK | Done |
| Buildozer pin `charset-normalizer==3.4.9` (host-pip android wheel) | Superseded — use `PIP_CONSTRAINT` |
| GitHub Actions cloud Android APK workflow | Done |
| CI `constraints.txt` + `PIP_CONSTRAINT` for charset-normalizer | Done |
| Android full-screen layout (no desktop Window.size) + API 35 + phone sim | Done |
| Dark theme + chip/camera polish + on-device diagnostics | Done |

Stack: NumPy + OpenCV in `core/`, Kivy UI in `colorsight/`, Buildozer packaging.

## Phase 2 — System-wide filter *(parked / later)*

**Not implemented.** When requested:

- Android system-wide **4×4 SurfaceFlinger color matrix** applied via **Shizuku** (or equivalent privileged bridge)
- Map the user’s `CorrectionProfile` matrix into a display color transform so *all* apps get the correction
- Requires separate permissions / user setup for Shizuku; out of scope for Phase 1 APK

Do not start Phase 2 until Phase 1 device checklist in `production.md` is signed off and this phase is explicitly requested.
