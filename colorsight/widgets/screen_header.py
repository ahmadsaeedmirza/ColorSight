"""Consistent screen header: back + gap + title (safe top padding)."""

from __future__ import annotations

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from colorsight.theme.tokens import Colors, Fonts, Icons, Spacing
from colorsight.widgets.primary_button import RoundIconButton


class ScreenHeader(BoxLayout):
    """Back button with a clear gap before the title; ≥44 dp tap target.

    Always includes ``Spacing.safe_top`` / ``screen_top`` so titles clear the
    status bar / notch on edge-to-edge Android.
    """

    def __init__(
        self,
        title: str = "",
        *,
        show_back: bool = True,
        on_back=None,
        trailing=None,
        include_top_inset: bool = True,
        title_color=None,
        back_bg=None,
        back_icon_color=None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint_y = None
        top = dp(Spacing.safe_top if include_top_inset else 0)
        self.padding = [0, top, 0, 0]
        self.height = dp(48) + top
        self.spacing = dp(Spacing.header_gap)

        fg = title_color if title_color is not None else Colors.text
        if show_back:
            btn = RoundIconButton(icon=Icons.arrow_back, diameter=44)
            btn.bg_color = back_bg if back_bg is not None else Colors.surface
            btn.icon_color = (
                back_icon_color if back_icon_color is not None else Colors.text
            )
            btn.on_press_cb = (lambda *_: on_back()) if callable(on_back) else None
            self.add_widget(btn)
        else:
            self.add_widget(Widget(size_hint=(None, None), size=(dp(4), dp(44))))

        title_lbl = Label(
            text=title,
            font_name=Fonts.bold,
            font_size=dp(20),
            color=fg,
            halign="left",
            valign="middle",
            shorten=True,
            shorten_from="right",
            max_lines=1,
        )
        title_lbl.bind(size=lambda *_: setattr(title_lbl, "text_size", title_lbl.size))
        self.add_widget(title_lbl)

        if trailing is not None:
            self.add_widget(trailing)
