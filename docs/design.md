# Design system

Reference language: vibrant pastel **notes app** — light canvas, bold rounded sans titles, colorful rounded cards, floating dark pill navigation with a blue center action.

## Brand & typography

| Token | Value |
|-------|--------|
| Display / titles | **Lexend Bold / SemiBold** (`assets/fonts/Lexend-Bold.ttf`, `Lexend-SemiBold.ttf`) |
| Body / UI | **Lexend Regular / Medium** |
| Title scale | Large hero titles (~32–40sp), screen headers (~22–26sp), card titles (~16–18sp) |
| Subtitle | Softer gray, medium weight, generous line spacing |

Lexend is bundled (OFL) so Android and desktop match.

## Color tokens

### Surfaces & text

| Token | Hex | Use |
|-------|-----|-----|
| `bg` | `#F6F4F1` | App background |
| `surface` | `#FFFFFF` | Search bar, light chips |
| `text` | `#1C1C1C` | Primary text |
| `text_muted` | `#6B6B6B` | Subtitles, hints |
| `nav_bg` | `#1E1E1E` | Floating bottom pill |
| `nav_icon` | `#F5F5F5` | Inactive nav icons |
| `nav_icon_active` | `#FFFFFF` | Active nav emphasis |
| `accent_blue` | `#4C8DFF` | Center FAB / primary actions |
| `accent_dark` | `#1E1E1E` | Dark round CTA (Welcome arrow) |

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
| `radius_chip` | 999 (pill) | Chips, search, nav pill |
| `radius_button` | 22 dp | Primary buttons |
| `radius_fab` | 999 (circle) | Center nav action, Welcome arrow |

## Spacing

| Token | Value |
|-------|-------|
| `space_xs` | 6 |
| `space_sm` | 10 |
| `space_md` | 16 |
| `space_lg` | 24 |
| `space_xl` | 32 |
| Screen horizontal padding | 20–24 |
| Card grid gap | 12–14 |
| Nav bottom inset | ~16–24 above home indicator |

## Elevation & motion

- **Soft shadows**: slightly offset darker rounded layer under cards (low alpha).
- **Tap**: brief scale-down (~0.96–0.98) then spring back; 80–160 ms feel.
- Avoid heavy glow / multi-layer neon; keep pastel and soft.

## Components

| Widget | Role |
|--------|------|
| `RoundedCard` | Base white/tinted card with radius + soft shadow |
| `PastelCard` | Colored note card + optional accent dot, title, subtitle, tap callback |
| `Chip` | Pill filter chip (selected / unselected) |
| `PillSearchBar` | Full-width pill search field (shell; may be decorative until search exists) |
| `FloatingNavBar` | Dark floating pill + icons + round blue center action |
| `PrimaryButton` | Filled CTA (dark or accent blue) |

## Screen list

| Screen id | Purpose (Phase 0) |
|-----------|-------------------|
| `welcome` | Big title, subtitle, dark arrow CTA, stacked pastel feature cards |
| `home` | Header (menu + avatar), chips, pastel feature grid |
| `test` | Placeholder — color vision test |
| `photos` | Placeholder — image correction |
| `camera` | Placeholder — live camera correction |
| `lens` | Placeholder — magnifier + color naming |
| `profile` | Placeholder — correction profile |
| `settings` | Placeholder — app settings |

## Layout recipes

### Welcome (first phone)

- Light background
- Large left-aligned title + muted subtitle
- Dark circular arrow button
- Vertical stack of large pastel cards (Test, Photos, Camera, Lens) with accent dots

### Home (second phone)

- Top row: menu affordance + circular avatar
- Optional pill search
- Horizontal chip row: All, Test, Photos, Camera
- 2-column grid of pastel feature cards
- Floating dark pill nav fixed at bottom (content padded above it)

## Accessibility notes (Phase 0+)

- High-contrast text on pastels (dark `#1C1C1C` on light fills)
- Large tap targets (≥44 dp)
- Color is never the only cue — titles and icons accompany pastel fills (Phase 1 features must keep this)
