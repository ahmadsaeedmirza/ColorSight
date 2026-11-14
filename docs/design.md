# Design system

Reference language: vibrant pastel **notes app** — light canvas, bold rounded sans titles, colorful rounded cards, floating dark pill navigation with a blue center action.

Color math (simulation, correction, naming) lives in `/core` and is documented in `architecture.md` — this file stays UI/visual only. Future screens should call `core` APIs rather than reimplement transforms.

## Naming rule (Kivy)

**Never name a custom widget class after a built-in Kivy widget** (`ProgressBar`, `Button`, `Label`, `Slider`, `Image`, `Switch`, `TextInput`, `CheckBox`, `Spinner`, `Popup`, `ScrollView`, layout class names, etc.).

Kivy auto-applies `style.kv` rules by class name. A custom `ProgressBar` inherits the stock rule and crashes (e.g. missing `max`). Prefer prefixed names: `PillProgressBar`, `PrimaryButton`, `PastelCard`, `HueStrip`.

## Brand & typography

| Token | Value |
|-------|--------|
| Display / titles | **Lexend Bold / SemiBold** (`assets/fonts/Lexend-*.ttf`) |
| Body / UI | **Lexend Regular / Medium** |
| Icons | **Material Icons** ligatures (`assets/icons/MaterialIcons-Regular.ttf`, Apache 2.0) via `Icon` widget |
| Title scale | Large hero titles (~32–40sp), screen headers (~22–26sp), card titles (~16–18sp) |
| Subtitle | Softer gray, medium weight, generous line spacing |

Lexend is bundled (OFL). Never use Lexend (or emoji) for UI icons — always `Fonts.icons` / `Icon`.

## Icon set

Registered as `Fonts.icons` (`MaterialIcons`). Use ligature names from `Icons` in `tokens.py`:

| Token | Ligature | Where |
|-------|----------|--------|
| `menu` | `menu` | Home header |
| `search` | `search` | Pill search bar |
| `home` | `home` | Floating nav |
| `photos` | `photo_library` | Floating nav |
| `camera` | `photo_camera` | Nav / features |
| `lens` | `loupe` | Floating nav |
| `profile` | `person` | Nav + avatar |
| `settings` | `settings` | Home grid |
| `add` | `add` | Center FAB |
| `arrow_forward` | `arrow_forward` | Welcome CTA |
| `arrow_back` | `arrow_back` | Placeholder / Photos back |
| `save` | `save` | Photos toolbar |
| `share` | `share` | Photos share |
| `compare` | `compare` | Comparison export (optional) |
| `drag_handle` | `drag_handle` | Before/after divider knob |
| `add_photo` | `add_photo_alternate` | Photos empty state (optional) |
| `tune` | `tune` | Severity / preview strength |
| `check` | `check` | Confirmations |

Helper: `colorsight.widgets.Icon` — consistent glyph size, color, and font registration.

### Icon sizing rule (mandatory)

`Icon` is a Kivy `Label`. Kivy’s widget property **`size` must be `(width, height)`** — never a single float.

| Do | Don’t |
|----|--------|
| `Icon(icon=Icons.home, icon_size=28)` | `Icon(..., size=dp(28))` |
| `icon_size` = glyph size in dp (default **24**) | Passing numeric `size=` (crashes `ListProperty`) |

`icon_size` drives `font_size` and a stable square layout box. Use `size=(w, h)` only when you intentionally set the widget box.

## Color tokens

### Surfaces & text

| Token | Hex | Use |
|-------|-----|-----|
| `bg` | `#F6F4F1` | App background |
| `surface` | `#FFFFFF` | Search bar, light chips |
| `text` | `#1C1C1C` | Primary text |
| `text_muted` | `#6B6B6B` | Subtitles, hints |
| `nav_bg` | `#1E1E1E` | Floating bottom pill |
| `nav_icon` | muted light gray | Inactive nav icons |
| `nav_icon_active` | `#FFFFFF` | Active nav emphasis |
| `accent_blue` | `#4C8DFF` | Center FAB / primary actions |
| `accent_dark` | `#1E1E1E` | Dark round CTA (Welcome arrow) |
| `chip_selected_bg` | `#1E1E1E` | Selected chip fill |
| `chip_selected_text` | `#FFFFFF` | Selected chip label (must stay visible) |
| `chip_bg` / `chip_text` | white / `#1C1C1C` | Unselected chips |

### Pastel cards (+ stronger accent dots)

| Name | Card fill | Accent dot |
|------|-----------|------------|
| Yellow | `#FFE56A` | `#E6B800` |
| Pink | `#FFB7C8` | `#FF5C8A` |
| Sky | `#B7DFFF` | `#3B9EE8` |
| Mint | `#C6F0D6` | `#2FBB78` |
| Peach | `#FFD2B8` | `#FF8A54` |
| Lavender | `#DDD0FF` | `#8B6FDB` |

## Radii

| Token | Value | Use |
|-------|-------|-----|
| `radius_card` | 24 dp | Feature / note cards |
| `radius_card_lg` | 28 dp | Hero stacked cards |
| `radius_chip` | 999 (pill intent) | Chips, search, nav pill |
| `radius_button` | 22 dp | Primary buttons |
| `radius_fab` | 999 (circle intent) | Center nav action, Welcome arrow |

### Radius clamping rule (mandatory)

Kivy does **not** clamp large radii. Passing `999` produces stretched ovals.

**Always** draw with:

```text
r = min(radius, width/2, height/2)
```

Helper: `colorsight.theme.geometry.clamp_radius` / `clamped_radii`.

Apply the **same** clamped value to fill **and** matching shadow layers. Used by `RoundedCard`, chips, search bar, nav pill, and buttons.

## Spacing

| Token | Value |
|-------|-------|
| `space_xs` … `space_xl` | 6 / 10 / 16 / 24 / 32 |
| Screen horizontal padding | 20–24 |
| Card grid gap | 12–14 |
| `nav_margin` | 18 dp (16–20) side inset for floating nav |
| `nav_height` | 64 dp pill |
| `nav_fab_size` | 52 dp |
| `nav_clearance` | 120 dp bottom padding on every screen that shows the nav |

## Elevation & motion

- **Soft shadows**: slightly offset darker rounded layer under cards (low alpha); same clamped radius as fill.
- **Tap**: brief opacity dip; 80–160 ms feel.
- Avoid heavy glow / multi-layer neon; keep pastel and soft.

## Components

| Widget | Role |
|--------|------|
| `Icon` | Material Icons ligature label — size via **`icon_size`**, not Kivy `size=` float |
| `RoundedCard` | Base card with clamped radius + soft shadow |
| `PastelCard` | Colored note card + accent dot, title, subtitle |
| `Chip` / `ChipRow` | Pill filters — selected = dark + **white** label; unselected = white + dark label, vertically centered |
| `PillSearchBar` | Capsule search with Material `search` icon |
| `FloatingNavBar` | Dark pill, equal slots, labels for all items, raised blue `add` FAB; fits width with side margins |
| `PrimaryButton` / `RoundIconButton` | Filled CTA / circular icon button |
| `PillProgressBar` (test) | Thin capsule progress (**not** named `ProgressBar` — avoids Kivy builtin clash) |
| `ArrowPad` / `ArrowKey` (test) | D-pad cross (76 dp keys, centered icons, soft shadow, press feedback) + full-width “I can't see it” |
| `AxisBars` (test) | Row per axis: pastel dot + Protan/Deutan/Tritan + ×cutoff value; bar with 1.0× tick |
| `SeverityBar` (test) | Capsule + numeric “N / 100” label |
| `Numpad` (test) | Legacy digit pad (plates flow retired from UI) |
| `HueStrip` (test) | Tap-to-swap hue tiles for arrangement step |
| `BeforeAfterViewer` (photos) | Pinch/pan stage + before/after divider (round white handle + Material `drag_handle`) |
| `PhotoModeToolbar` (photos) | Dark pill Original \| Corrected \| Simulation + Save + Share (`mode_cb` / `save_cb` / `share_cb`) |
| `PreviewSeverityBar` (photos) | Strength track (**not** `Slider`); percent snap; `change_cb` — preview only |
| `TextLinkButton` (photos) | “Reset to my result” text action |
| `LoadingShimmer` (photos) | Thin animated bar while bg-thread preview/save runs |

## Screen list

| Screen id | Purpose |
|-----------|---------|
| `welcome` | Big title, subtitle, dark arrow CTA, stacked pastel feature cards |
| `home` | Header (menu + avatar), chips, pastel feature grid |
| `test` | **Vision test** — checklist → Trivector Landolt C → hue arrange → results (Save profile) |
| `photos` | **Image correction** — profile gate, pick, before/after, modes, save/share, comparison |
| `camera` / `lens` / `profile` / `settings` | Placeholders (Phase 1 remaining) |

### Photos screen recipe

- **No profile:** pink `PastelCard` + “Go to Vision Test” (never show paths).
- **Empty:** pink card + large “Choose a photo”.
- **Viewer:** pinch/pan; Original = full image (no divider); Corrected/Simulation = before/after with corner labels + ≥44 dp handle at 50%.
- **Strength:** defaults to test result; hint + “Reset to my result” when changed; Simulation helper: “Adjust the strength until it matches how you see it.”
- **Actions:** Save/Share current mode; Export comparison (“Normal vision” / “How I see it”); confirmations without paths.
- Bottom padding = `nav_clearance`.

### Test screen recipe

- **Checklist** (yellow/mint, `PastelCard(auto_height=True)`): brightness / night mode / ~40 cm / glasses  
- **Trivector**: “Question N” + progress capsule; Landolt C ~170 dp from a **512 px** texture (linear filter); prompt with clear gap above a **D-pad** (Up / Left·Right / Down, empty center); “I can't see it” full width; ~6 s timeout. Trial shell is **reused** (texture blit only) so the tree is not rebuilt each question. Fits 360×640 with scroll clearance.  
- **Hue** then **results**: type card; severity bar with “N / 100”; axis rows with labels + ×cutoff + 1.0× tick; yellow disclaimer with **auto-height** wrapped text (no clipping); before/after swatches; **Save my profile**  
- After save: **“Your color profile has been saved”** (never show file paths)

### PastelCard text fit

Use `auto_height=True` when the subtitle must wrap fully: subtitle `text_size` follows width, height follows `texture_size`, card height sums content + padding.

### Floating nav

- Five **identical** slots: Material icon above label, shared baseline (including Camera)  
- Blue center **+** FAB sits on the Camera slot, raised slightly but **fully inside** the nav pill; horizontally clamped so it cannot spill outside the bar at narrow (~360) or wide widths

## Layout recipes

### Welcome

- Light background; Lexend title; Material `arrow_forward` CTA
- Stacked pastel cards; no floating nav (hidden)

### Home

- Menu `Icon` + circular avatar (`person`)
- Pill search + chips (All / Test / Photos / Camera)
- 2-column pastel grid inside ScrollView
- Floating nav with 18dp side margins; content bottom padding = `nav_clearance`

## Accessibility notes (Phase 0+)

- High-contrast text on pastels and on selected chips (white on dark)
- Large tap targets (≥44 dp)
- Color is never the only cue — titles and icons accompany pastel fills
