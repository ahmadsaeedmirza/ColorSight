"""Floating dark pill bottom navigation with centered blue action."""

from kivy.metrics import dp
from kivy.properties import ObjectProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse, RoundedRectangle

from colorsight.theme.geometry import clamped_radii
from colorsight.theme.tokens import Colors, Fonts, Icons, Radii, Spacing
from colorsight.widgets.icon import Icon


class _NavItem(ButtonBehavior, BoxLayout):
    """Identical slot: icon above label, shared baseline for every tab including Camera."""

    def __init__(self, key, icon_name, label, active=False, on_tap=None, **kwargs):
        super().__init__(**kwargs)
        self.key = key
        self._on_tap = on_tap
        self.orientation = "vertical"
        self.size_hint = (1, 1)
        self.padding = [dp(2), dp(8), dp(2), dp(6)]
        self.spacing = dp(2)

        self._glyph = Icon(
            icon=icon_name,
            icon_size=22,
            color=Colors.nav_icon_active if active else Colors.nav_icon,
            size_hint=(1, None),
            height=dp(24),
        )
        self._caption = Label(
            text=label,
            font_name=Fonts.semibold if active else Fonts.medium,
            font_size=dp(9),
            color=Colors.nav_icon_active if active else (0.65, 0.65, 0.65, 1),
            size_hint=(1, None),
            height=dp(14),
            halign="center",
            valign="middle",
            shorten=True,
            shorten_from="right",
        )
        self._caption.bind(size=lambda *_: setattr(self._caption, "text_size", self._caption.size))
        self.add_widget(self._glyph)
        self.add_widget(self._caption)

    def set_active(self, active: bool):
        self._glyph.color = Colors.nav_icon_active if active else Colors.nav_icon
        self._caption.color = Colors.nav_icon_active if active else (0.65, 0.65, 0.65, 1)
        self._caption.font_name = Fonts.semibold if active else Fonts.medium

    def on_release(self):
        if callable(self._on_tap):
            self._on_tap(self.key)


class _CenterFab(ButtonBehavior, Widget):
    def __init__(self, on_tap=None, **kwargs):
        super().__init__(**kwargs)
        self._on_tap = on_tap
        self.size_hint = (None, None)
        d = dp(Spacing.nav_fab_size)
        self.size = (d, d)
        self._icon = Icon(
            icon=Icons.add,
            icon_size=24,
            color=(1, 1, 1, 1),
            size_hint=(None, None),
            size=(d, d),
        )
        self.add_widget(self._icon)
        self.bind(pos=self._redraw, size=self._redraw)
        self._redraw()

    def _redraw(self, *_args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*Colors.shadow)
            Ellipse(pos=(self.x, self.y - dp(2)), size=self.size)
            Color(*Colors.accent_blue)
            Ellipse(pos=self.pos, size=self.size)
        self._icon.pos = self.pos
        self._icon.size = self.size

    def on_release(self):
        if callable(self._on_tap):
            self._on_tap("camera")


class FloatingNavBar(FloatLayout):
    """Dark floating pill: five equal slots + raised blue + centered on Camera."""

    active = StringProperty("home")
    on_navigate = ObjectProperty(None, allownone=True)

    _ITEMS = (
        ("home", Icons.home, "Home"),
        ("photos", Icons.photos, "Photos"),
        ("camera", Icons.camera, "Camera"),
        ("lens", Icons.lens, "Lens"),
        ("profile", Icons.profile, "Profile"),
    )

    def __init__(self, **kwargs):
        kwargs.setdefault("size_hint", (None, None))
        super().__init__(**kwargs)
        self._item_widgets = {}
        self._pill = Widget(size_hint=(None, None))
        self.add_widget(self._pill)

        self._row = BoxLayout(
            orientation="horizontal",
            size_hint=(None, None),
            spacing=0,
            padding=[dp(6), 0, dp(6), 0],
        )
        self.add_widget(self._row)

        self._fab = _CenterFab(on_tap=self._tap)
        self.add_widget(self._fab)

        self._sync_height()
        self._build_items()
        self.bind(pos=self._layout, size=self._layout, active=self._sync_active)
        self._layout()

    def _sync_height(self):
        pill_h = dp(Spacing.nav_height)
        fab_d = dp(Spacing.nav_fab_size)
        # Keep FAB fully inside this widget (slight raise above pill midline)
        raise_px = min(fab_d * 0.28, dp(16))
        self.height = pill_h + raise_px

    def _build_items(self):
        self._row.clear_widgets()
        self._item_widgets.clear()
        for key, icon_name, label in self._ITEMS:
            item = _NavItem(
                key,
                icon_name,
                label,
                active=(key == self.active),
                on_tap=self._tap,
            )
            self._row.add_widget(item)
            self._item_widgets[key] = item

    def _layout(self, *_args):
        self._sync_height()
        pill_h = dp(Spacing.nav_height)
        self._pill.size = (max(0, self.width), pill_h)
        self._pill.pos = (self.x, self.y)
        radii = clamped_radii(dp(Radii.chip), self._pill.width, self._pill.height)
        self._pill.canvas.before.clear()
        with self._pill.canvas.before:
            Color(*Colors.shadow)
            RoundedRectangle(
                pos=(self._pill.x, self._pill.y - dp(3)),
                size=self._pill.size,
                radius=radii,
            )
            Color(*Colors.nav_bg)
            RoundedRectangle(pos=self._pill.pos, size=self._pill.size, radius=radii)

        self._row.size = (self.width, pill_h)
        self._row.pos = (self.x, self.y)

        fab_d = dp(Spacing.nav_fab_size)
        # Clamp FAB diameter so it never wider than a single slot
        slot_w = self.width / 5.0 if self.width else fab_d
        fab_d = min(fab_d, max(dp(40), slot_w * 0.85))
        self._fab.size = (fab_d, fab_d)
        # Center on the middle (camera) slot — index 2 of 5
        pad = dp(6)
        inner_w = max(0, self.width - 2 * pad)
        slot = inner_w / 5.0
        cam_center_x = self.x + pad + slot * 2.5
        self._fab.center_x = cam_center_x
        # Sit mostly on the pill; top flush with widget top
        self._fab.y = self.y + self.height - fab_d
        # Hard clamp horizontally inside the nav
        if self._fab.x < self.x + dp(4):
            self._fab.x = self.x + dp(4)
        if self._fab.right > self.x + self.width - dp(4):
            self._fab.x = self.x + self.width - dp(4) - self._fab.width

    def _tap(self, key: str):
        self.active = key
        if callable(self.on_navigate):
            self.on_navigate(key)

    def _sync_active(self, *_args):
        for key, widget in self._item_widgets.items():
            if isinstance(widget, _NavItem):
                widget.set_active(key == self.active)
