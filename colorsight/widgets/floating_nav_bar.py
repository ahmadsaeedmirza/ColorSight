"""Floating dark pill bottom navigation with blue center action."""

from kivy.metrics import dp
from kivy.properties import ListProperty, ObjectProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse, RoundedRectangle

from colorsight.theme.tokens import Colors, Fonts, Radii, Spacing


class _NavItem(ButtonBehavior, BoxLayout):
    def __init__(self, key, glyph, label, active=False, on_tap=None, **kwargs):
        super().__init__(**kwargs)
        self.key = key
        self._on_tap = on_tap
        self.orientation = "vertical"
        self.size_hint = (1, 1)
        self.padding = [0, dp(8)]
        self.spacing = dp(2)

        self._glyph = Label(
            text=glyph,
            font_size=dp(18),
            color=Colors.nav_icon_active if active else Colors.nav_icon,
            size_hint_y=None,
            height=dp(22),
        )
        self._caption = Label(
            text=label,
            font_name=Fonts.medium,
            font_size=dp(10),
            color=Colors.nav_icon_active if active else (0.65, 0.65, 0.65, 1),
            size_hint_y=None,
            height=dp(14),
        )
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
        self.size = (dp(56), dp(56))
        self.bind(pos=self._redraw, size=self._redraw)
        self._redraw()

    def _redraw(self, *_args):
        self.canvas.clear()
        with self.canvas:
            Color(*Colors.shadow)
            Ellipse(pos=(self.x, self.y - dp(2)), size=self.size)
            Color(*Colors.accent_blue)
            Ellipse(pos=self.pos, size=self.size)
            Color(1, 1, 1, 1)
            # plus glyph via nested small rects
            cx, cy = self.center_x, self.center_y
            w, h = dp(18), dp(3)
            RoundedRectangle(pos=(cx - w / 2, cy - h / 2), size=(w, h), radius=[dp(2)])
            RoundedRectangle(pos=(cx - h / 2, cy - w / 2), size=(h, w), radius=[dp(2)])

    def on_release(self):
        if callable(self._on_tap):
            self._on_tap("camera")


class FloatingNavBar(BoxLayout):
    """Dark floating pill with Home / Photos / [FAB] / Lens / Profile."""

    active = StringProperty("home")
    on_navigate = ObjectProperty(None, allownone=True)

    # (key, glyph, label)
    items = ListProperty(
        [
            ("home", "⌂", "Home"),
            ("photos", "▣", "Photos"),
            ("camera", "+", "Camera"),  # center FAB overrides glyph
            ("lens", "◎", "Lens"),
            ("profile", "☺", "Profile"),
        ]
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint = (1, None)
        self.height = dp(Spacing.nav_height)
        self.padding = [dp(10), dp(4), dp(10), dp(4)]
        self.spacing = dp(2)
        self._item_widgets = {}
        self.bind(pos=self._redraw, size=self._redraw, active=self._sync_active)
        self._build()
        self._redraw()

    def _build(self):
        self.clear_widgets()
        self._item_widgets.clear()
        for key, glyph, label in self.items:
            if key == "camera":
                fab = _CenterFab(on_tap=self._tap)
                slot = BoxLayout(size_hint=(None, 1), width=dp(64), padding=[dp(4), 0])
                slot.add_widget(fab)
                self.add_widget(slot)
                self._item_widgets[key] = fab
            else:
                item = _NavItem(key, glyph, label, active=(key == self.active), on_tap=self._tap)
                self.add_widget(item)
                self._item_widgets[key] = item

    def _redraw(self, *_args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*Colors.shadow)
            RoundedRectangle(
                pos=(self.x, self.y - dp(3)),
                size=(self.width, self.height),
                radius=[dp(Radii.chip)],
            )
            Color(*Colors.nav_bg)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(Radii.chip)])

    def _tap(self, key: str):
        self.active = key
        if callable(self.on_navigate):
            self.on_navigate(key)

    def _sync_active(self, *_args):
        for key, widget in self._item_widgets.items():
            if isinstance(widget, _NavItem):
                widget.set_active(key == self.active)
