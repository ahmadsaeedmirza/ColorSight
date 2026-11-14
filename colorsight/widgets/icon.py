"""Material Icons helper — ligature-based icon label."""

from kivy.metrics import dp
from kivy.properties import ColorProperty, NumericProperty, StringProperty
from kivy.uix.label import Label

from colorsight.theme.tokens import Colors, Fonts, Icons


class Icon(Label):
    """Renders a Material Icons glyph by ligature name (e.g. ``menu``, ``home``).

    Use ``icon_size`` (numeric dp intent, default 24) for the glyph. Do **not**
    pass Kivy's widget ``size=`` a single float — ``size`` must be ``(w, h)``.
    """

    icon = StringProperty(Icons.home)
    icon_size = NumericProperty(24)
    color = ColorProperty(Colors.text)

    def __init__(self, icon=Icons.home, icon_size=24, color=None, **kwargs):
        # Guard against size=28 / size=dp(28) which crashes ListProperty
        if "size" in kwargs and not isinstance(kwargs["size"], (list, tuple)):
            raise TypeError(
                "Icon: pass glyph size as icon_size=… (e.g. icon_size=28). "
                "Kivy widget size= must be a (width, height) list/tuple."
            )
        kwargs.setdefault("size_hint", (None, None))
        super().__init__(**kwargs)
        self.icon = icon
        self.icon_size = icon_size
        if color is not None:
            self.color = color
        self.font_name = Fonts.icons
        self.halign = "center"
        self.valign = "middle"
        self.markup = False
        self._apply()
        self.bind(
            icon=self._apply,
            icon_size=self._apply,
            size=self._sync_text_size,
            pos=self._sync_text_size,
        )

    def _apply(self, *_args):
        self.text = self.icon
        self.font_name = Fonts.icons
        self.font_size = dp(self.icon_size)
        side = dp(max(self.icon_size + 4, 24))
        if self.size_hint_x is None and self.size_hint_y is None:
            # Keep a stable tap/layout box when used as a fixed icon.
            if self.width <= 1 or self.height <= 1:
                self.size = (side, side)
        self._sync_text_size()

    def _sync_text_size(self, *_args):
        self.text_size = self.size
