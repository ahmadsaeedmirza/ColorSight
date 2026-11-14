"""Floating dark pill bottom navigation with raised blue center action."""

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
    def __init__(self, key, icon_name, label, active=False, on_tap=None, **kwargs):
        super().__init__(**kwargs)
        self.key = key
        self._on_tap = on_tap
        self.orientation = "vertical"
        self.size_hint = (1, 1)
        self.padding = [dp(2), dp(6), dp(2), dp(4)]
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
            font_name=Fonts.medium,
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


class _CenterFab(ButtonBehavior, FloatLayout):
    def __init__(self, on_tap=None, **kwargs):
        super().__init__(**kwargs)
        self._on_tap = on_tap
        self.size_hint = (None, None)
        d = dp(Spacing.nav_fab_size)
        self.size = (d, d)
        self._icon = Icon(
            icon=Icons.add,
            icon_size=26,
            color=(1, 1, 1, 1),
            size_hint=(None, None),
            size=(d, d),
        )
        self.add_widget(self._icon)
        self.bind(pos=self._layout, size=self._layout)
        self._layout()

    def _layout(self, *_args):
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
    """Dark floating pill with Home / Photos / [FAB] / Lens / Profile."""

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
            padding=[dp(4), 0, dp(4), 0],
        )
        self.add_widget(self._row)

        self._fab = _CenterFab(on_tap=self._tap)
        self.add_widget(self._fab)

        # Contain the raised FAB fully (hit-testing + no clip)
        self._sync_height()
        self._build_items()
        self.bind(
            pos=self._layout,
            size=self._layout,
            active=self._sync_active,
        )
        self._layout()

    def _sync_height(self):
        pill_h = dp(Spacing.nav_height)
        fab_d = dp(Spacing.nav_fab_size)
        overhang = fab_d * 0.42
        self.height = pill_h + overhang

    def _build_items(self):
        self._row.clear_widgets()
        self._item_widgets.clear()
        for key, icon_name, label in self._ITEMS:
            if key == "camera":
                # Spacer slot under the raised FAB; caption only
                slot = BoxLayout(orientation="vertical", size_hint=(1, 1))
                slot.add_widget(Widget(size_hint=(1, 1)))
                caption = Label(
                    text=label,
                    font_name=Fonts.medium,
                    font_size=dp(9),
                    color=(0.65, 0.65, 0.65, 1),
                    size_hint=(1, None),
                    height=dp(14),
                    halign="center",
                    valign="middle",
                )
                caption.bind(size=lambda *_ , c=caption: setattr(c, "text_size", c.size))
                slot.add_widget(caption)
                # Invisible tap target for camera via FAB; still keep slot for balance
                self._row.add_widget(slot)
                self._item_widgets[key] = caption
            else:
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
        self._pill.size = (self.width, pill_h)
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
        self._fab.size = (fab_d, fab_d)
        self._fab.center_x = self.center_x
        # Raised: top of FAB aligns with top of this widget; ~42% sits above the pill
        self._fab.y = self.y + self.height - fab_d

    def _tap(self, key: str):
        self.active = key
        if callable(self.on_navigate):
            self.on_navigate(key)

    def _sync_active(self, *_args):
        for key, widget in self._item_widgets.items():
            if isinstance(widget, _NavItem):
                widget.set_active(key == self.active)
            elif key == "camera" and isinstance(widget, Label):
                active = self.active == "camera"
                widget.color = Colors.nav_icon_active if active else (0.65, 0.65, 0.65, 1)
                widget.font_name = Fonts.semibold if active else Fonts.medium
