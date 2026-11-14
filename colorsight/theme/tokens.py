"""Design tokens for the ColorSight pastel notes-app language."""


class Colors:
    bg = (0.965, 0.957, 0.945, 1)  # #F6F4F1
    surface = (1, 1, 1, 1)
    text = (0.110, 0.110, 0.110, 1)  # #1C1C1C
    text_muted = (0.420, 0.420, 0.420, 1)  # #6B6B6B
    nav_bg = (0.118, 0.118, 0.118, 1)  # #1E1E1E
    nav_icon = (0.75, 0.75, 0.75, 1)
    nav_icon_active = (1, 1, 1, 1)
    accent_blue = (0.298, 0.553, 1.0, 1)  # #4C8DFF
    accent_dark = (0.118, 0.118, 0.118, 1)
    shadow = (0.10, 0.10, 0.12, 0.18)
    chip_selected_bg = (0.118, 0.118, 0.118, 1)
    chip_selected_text = (1, 1, 1, 1)
    chip_bg = (1, 1, 1, 1)
    chip_text = (0.110, 0.110, 0.110, 1)
    chip_border = (0.88, 0.86, 0.84, 1)
    divider = (0.90, 0.88, 0.86, 1)


# name -> (fill rgba, accent rgba)
PASTEL_PALETTE = {
    "yellow": ((1.0, 0.898, 0.416, 1), (0.902, 0.722, 0.0, 1)),
    "pink": ((1.0, 0.718, 0.784, 1), (1.0, 0.361, 0.541, 1)),
    "sky": ((0.718, 0.875, 1.0, 1), (0.231, 0.620, 0.910, 1)),
    "mint": ((0.776, 0.941, 0.839, 1), (0.184, 0.733, 0.471, 1)),
    "peach": ((1.0, 0.824, 0.722, 1), (1.0, 0.541, 0.329, 1)),
    "lavender": ((0.867, 0.816, 1.0, 1), (0.545, 0.435, 0.859, 1)),
}


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
