"""Home screen — feature grid with working chips and avatar → Profile."""

from __future__ import annotations

from kivy.metrics import dp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse

from colorsight.theme.tokens import Colors, Fonts, Icons, Spacing
from colorsight.widgets import ChipRow, Icon, PastelCard


class _AvatarButton(ButtonBehavior, Widget):
    """Tappable avatar — opens Profile."""

    def __init__(self, on_tap=None, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (dp(44), dp(44))
        self._on_tap = on_tap
        self._icon = Icon(
            icon=Icons.profile,
            icon_size=22,
            color=(1, 1, 1, 1),
            size_hint=(None, None),
            size=(dp(44), dp(44)),
        )
        self.add_widget(self._icon)
        self.bind(pos=self._draw, size=self._draw)
        self._draw()

    def _draw(self, *_args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*Colors.accent_blue)
            Ellipse(pos=self.pos, size=self.size)
        self._icon.pos = self.pos
        self._icon.size = self.size

    def on_release(self):
        if callable(self._on_tap):
            self._on_tap()


class _MenuButton(ButtonBehavior, BoxLayout):
    def __init__(self, on_tap=None, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (dp(44), dp(44))
        self._on_tap = on_tap
        self.add_widget(
            Icon(
                icon=Icons.menu,
                icon_size=26,
                color=Colors.text,
                size_hint=(1, 1),
            )
        )

    def on_release(self):
        if callable(self._on_tap):
            self._on_tap()


class HomeScreen(Screen):
    _FEATURES = [
        ("Vision Test", "Trivector color check", "yellow", "test", 150),
        ("Photos", "Fix gallery colors", "pink", "photos", 150),
        ("Camera", "Live correction", "sky", "camera", 170),
        ("Lens", "Name that color", "mint", "lens", 170),
        ("Profile", "Your correction", "peach", "profile", 150),
        ("Settings", "Preferences", "lavender", "settings", 150),
    ]

    def __init__(self, **kwargs):
        super().__init__(name="home", **kwargs)
        self._filter = "All"
        self._chips = None
        self._build()
        self.bind(on_pre_enter=self._on_pre_enter)

    def _on_pre_enter(self, *_a):
        self._reset_chip_scroll()

    def _reset_chip_scroll(self):
        from kivy.clock import Clock

        def _go(_dt=None):
            if self._chips is not None and hasattr(self._chips, "reset_scroll"):
                self._chips.reset_scroll()

        Clock.schedule_once(_go, 0)

    def apply_theme(self):
        self._build()
        self._reset_chip_scroll()

    def _open(self, screen_name):
        def _handler(_card=None):
            if not self.manager:
                return
            parent = self.manager.parent
            # Lens is a Camera loupe state — go through RootShell navigation
            if screen_name == "lens" and hasattr(parent, "_navigate"):
                parent._navigate("lens")
                return
            if hasattr(parent, "ensure_screen") and not parent.ensure_screen(screen_name):
                return
            if screen_name not in self.manager.screen_names:
                return
            self.manager.transition.direction = "left"
            self.manager.current = screen_name
            if hasattr(parent, "set_nav_active"):
                parent.set_nav_active(screen_name)

        return _handler

    def _on_chip(self, selected: str):
        mapping = {
            "All": None,
            "Test": "test",
            "Photos": "photos",
            "Camera": "camera",
            "Lens": "lens",
            "Profile": "profile",
        }
        # Chip row filters the grid; tapping a feature chip also jumps there
        self._filter = selected
        self._rebuild_grid()
        target = mapping.get(selected)
        if target and selected != "All" and self.manager:
            parent = self.manager.parent
            if target == "lens" and hasattr(parent, "_navigate"):
                parent._navigate("lens")
            elif hasattr(parent, "set_nav_active"):
                parent.set_nav_active(target)
            elif hasattr(parent, "ensure_screen") and parent.ensure_screen(target):
                self.manager.current = target

    def _build(self):
        self.clear_widgets()
        scroll = ScrollView(do_scroll_x=False, bar_width=0)
        # Left pad only — chip row scrolls flush to the right screen edge
        self._content = BoxLayout(
            orientation="vertical",
            padding=[
                dp(Spacing.screen_x),
                dp(Spacing.safe_top),
                0,
                dp(Spacing.nav_clearance),
            ],
            spacing=dp(Spacing.md),
            size_hint_y=None,
        )
        self._content.bind(minimum_height=self._content.setter("height"))

        def _right_pad(child):
            wrap = BoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=child.height,
                padding=[0, 0, dp(Spacing.screen_x), 0],
            )
            wrap.add_widget(child)
            child.bind(height=lambda *_: setattr(wrap, "height", child.height))
            return wrap

        header = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(44),
        )
        header.add_widget(_MenuButton(on_tap=self._open("settings")))
        header.add_widget(Widget())
        header.add_widget(_AvatarButton(on_tap=self._open("profile")))
        self._content.add_widget(_right_pad(header))

        greet = Label(
            text="Your toolkit",
            font_name=Fonts.bold,
            font_size=dp(26),
            color=Colors.text,
            halign="left",
            valign="middle",
            size_hint_y=None,
            height=dp(36),
        )
        greet.bind(size=lambda *_: setattr(greet, "text_size", greet.size))
        self._content.add_widget(_right_pad(greet))

        chips = ChipRow(
            options=["All", "Test", "Photos", "Camera", "Lens", "Profile"],
            selected="All",
        )
        chips.change_cb = self._on_chip
        self._chips = chips
        self._content.add_widget(chips)
        self._reset_chip_scroll()

        self._grid_host = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(1))
        self._content.add_widget(_right_pad(self._grid_host))
        self._rebuild_grid()

        scroll.add_widget(self._content)
        self.add_widget(scroll)

    def _rebuild_grid(self):
        self._grid_host.clear_widgets()
        filt = self._filter
        visible = []
        for title, sub, palette, screen, h in self._FEATURES:
            if filt == "All":
                visible.append((title, sub, palette, screen, h))
            elif filt == "Test" and screen == "test":
                visible.append((title, sub, palette, screen, h))
            elif filt.lower() == screen or (filt == "Lens" and screen == "lens"):
                visible.append((title, sub, palette, screen, h))
            elif filt == "Profile" and screen == "profile":
                visible.append((title, sub, palette, screen, h))

        if not visible:
            visible = list(self._FEATURES)

        # Pair into rows of 2
        rows = []
        for i in range(0, len(visible), 2):
            rows.append(visible[i : i + 2])
        gap = Spacing.grid_gap
        row_heights = []
        for row in rows:
            row_heights.append(max(h for *_rest, h in row))
        total_h = sum(row_heights) + gap * max(0, len(rows) - 1)

        grid = GridLayout(
            cols=2,
            spacing=dp(gap),
            size_hint_y=None,
            height=dp(total_h),
        )
        for title, sub, palette, screen, h in visible:
            card = PastelCard(
                title=title,
                subtitle=sub,
                palette=palette,
                size_hint_y=None,
                height=dp(h),
            )
            card.select_cb = self._open(screen)
            grid.add_widget(card)
        # Odd count: spacer
        if len(visible) % 2 == 1:
            grid.add_widget(Widget())

        self._grid_host.add_widget(grid)
        self._grid_host.height = grid.height
