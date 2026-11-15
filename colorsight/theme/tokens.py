"""Design tokens for the ColorSight pastel notes-app language (light + dark)."""

from __future__ import annotations


def _hex(h: str, a: float = 1.0) -> tuple[float, float, float, float]:
    h = h.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (r / 255.0, g / 255.0, b / 255.0, a)


# Always-light surfaces for Vision Test trials + Photos/Camera preview accuracy
NEUTRAL_BG = _hex("F6F4F1")
NEUTRAL_SURFACE = (1.0, 1.0, 1.0, 1.0)
NEUTRAL_TEXT = _hex("1C1C1C")
NEUTRAL_TEXT_MUTED = _hex("6B6B6B")

LIGHT_COLORS = {
    "bg": _hex("F6F4F1"),
    "surface": (1.0, 1.0, 1.0, 1.0),
    "text": _hex("1C1C1C"),
    "text_muted": _hex("6B6B6B"),
    "nav_bg": _hex("1E1E1E"),
    "nav_icon": (0.75, 0.75, 0.75, 1),
    "nav_icon_active": (1.0, 1.0, 1.0, 1.0),
    "accent_blue": _hex("4C8DFF"),
    "accent_dark": _hex("1E1E1E"),
    "shadow": (0.10, 0.10, 0.12, 0.18),
    "chip_selected_bg": _hex("1E1E1E"),
    "chip_selected_text": (1.0, 1.0, 1.0, 1.0),
    "chip_bg": (1.0, 1.0, 1.0, 1.0),
    "chip_text": _hex("1C1C1C"),
    "chip_border": (0.88, 0.86, 0.84, 1),
    "divider": (0.90, 0.88, 0.86, 1),
    "cant_see_bg": _hex("FFD2B8"),
    "cant_see_bg_pressed": _hex("FF8A54"),
    "cant_see_text": _hex("1C1C1C"),
    "toolbar_bg": (0.12, 0.12, 0.12, 0.92),
    "toolbar_text": (0.72, 0.72, 0.72, 1),
    "toolbar_text_active": (1.0, 1.0, 1.0, 1.0),
}

DARK_COLORS = {
    "bg": _hex("121214"),
    "surface": _hex("1E1E22"),
    "text": _hex("F2F2F2"),
    "text_muted": _hex("A0A0A8"),
    "nav_bg": _hex("2A2A2F"),
    "nav_icon": (0.70, 0.70, 0.74, 1),
    "nav_icon_active": (1.0, 1.0, 1.0, 1.0),
    "accent_blue": _hex("4C8DFF"),
    "accent_dark": _hex("3A3A42"),
    "shadow": (0.0, 0.0, 0.0, 0.45),
    "chip_selected_bg": _hex("F2F2F2"),
    "chip_selected_text": _hex("121214"),
    "chip_bg": _hex("2A2A2F"),
    "chip_text": _hex("F2F2F2"),
    "chip_border": _hex("3A3A42"),
    "divider": _hex("2A2A2F"),
    "cant_see_bg": _hex("FFD2B8"),
    "cant_see_bg_pressed": _hex("FF8A54"),
    "cant_see_text": _hex("1C1C1C"),
    "toolbar_bg": (0.18, 0.18, 0.20, 0.94),
    "toolbar_text": (0.70, 0.70, 0.74, 1),
    "toolbar_text_active": (1.0, 1.0, 1.0, 1.0),
}

PASTEL_PALETTE_LIGHT = {
    "yellow": (_hex("FFE56A"), _hex("E6B800")),
    "pink": (_hex("FFB7C8"), _hex("FF5C8A")),
    "sky": (_hex("B7DFFF"), _hex("3B9EE8")),
    "mint": (_hex("C6F0D6"), _hex("2FBB78")),
    "peach": (_hex("FFD2B8"), _hex("FF8A54")),
    "lavender": (_hex("DDD0FF"), _hex("8B6FDB")),
}

# Deeper fills + readable light text accents for dark UI chrome (not used on accuracy surfaces)
PASTEL_PALETTE_DARK = {
    "yellow": (_hex("4A3F14"), _hex("F0D060")),
    "pink": (_hex("4A2433"), _hex("FF8AAB")),
    "sky": (_hex("1A3348"), _hex("6BB7F0")),
    "mint": (_hex("1A3A2C"), _hex("5DD6A0")),
    "peach": (_hex("4A2E1C"), _hex("FFA070")),
    "lavender": (_hex("2E2648"), _hex("B09AFF")),
}


class _ColorBag:
    """Mutable color bag so `Colors.bg` always reflects the active theme."""

    def __init__(self, values: dict):
        self._apply(values)

    def _apply(self, values: dict):
        for k, v in values.items():
            setattr(self, k, v)


Colors = _ColorBag(LIGHT_COLORS)
PASTEL_PALETTE = dict(PASTEL_PALETTE_LIGHT)


def apply_color_set(resolved: str) -> None:
    """resolved: 'light' | 'dark' — mutates Colors + PASTEL_PALETTE in place."""
    global PASTEL_PALETTE
    src = DARK_COLORS if resolved == "dark" else LIGHT_COLORS
    Colors._apply(src)
    PASTEL_PALETTE.clear()
    PASTEL_PALETTE.update(
        PASTEL_PALETTE_DARK if resolved == "dark" else PASTEL_PALETTE_LIGHT
    )


class Radii:
    card = 24
    card_lg = 28
    chip = 999  # design intent: pill — always clamp via clamp_radius()
    button = 22
    fab = 999
    search = 999
    avatar = 999


class Spacing:
    xs = 6
    sm = 10
    md = 16
    lg = 24
    xl = 32
    screen_x = 22
    screen_top = 16  # Top safe padding under status / notch
    header_gap = 10  # Gap between back button and title
    grid_gap = 12
    nav_height = 64
    nav_margin = 18  # 16–20dp side inset
    nav_fab_size = 52
    nav_fab_raise = 12
    # Bottom content inset so scroll areas clear the floating nav (+ raised FAB)
    nav_clearance = 120


class Fonts:
    regular = "Lexend"
    medium = "LexendMedium"
    semibold = "LexendSemiBold"
    bold = "LexendBold"
    icons = "MaterialIcons"


class Icons:
    """Material Icons ligature names used in the shell."""

    menu = "menu"
    search = "search"
    home = "home"
    photos = "photo_library"
    camera = "photo_camera"
    lens = "loupe"
    profile = "person"
    settings = "settings"
    add = "add"
    arrow_forward = "arrow_forward"
    arrow_back = "arrow_back"
    arrow_upward = "arrow_upward"
    arrow_downward = "arrow_downward"
    save = "save"
    share = "share"
    compare = "compare"
    drag_handle = "drag_handle"
    add_photo = "add_photo_alternate"
    tune = "tune"
    check = "check"
    lock = "lock"
    lock_open = "lock_open"
    pause = "pause"
    play_arrow = "play_arrow"
    flip_camera = "flip_camera_android"
    loupe_toggle = "loupe"
    visibility_off = "visibility_off"
    content_copy = "content_copy"
    dark_mode = "dark_mode"
    light_mode = "light_mode"
