"""Shared placeholder layout for feature screens."""

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

from colorsight.theme.tokens import Colors, Fonts, Icons, Spacing
from colorsight.widgets import PastelCard, RoundIconButton


class PlaceholderScreen(Screen):
    """Simple titled placeholder with a pastel card and muted copy."""

    def __init__(
        self,
        name,
        title,
        subtitle,
        palette="lavender",
        show_back=True,
        **kwargs,
    ):
        super().__init__(name=name, **kwargs)
        self._title = title
        self._subtitle = subtitle
        self._palette = palette
        self._show_back = show_back
        self._build()

    def _go_back(self, *_a):
        if self.manager:
            self.manager.current = "home"

    def _build(self):
        scroll = ScrollView(do_scroll_x=False, bar_width=0)
        root = BoxLayout(
            orientation="vertical",
            padding=[
                dp(Spacing.screen_x),
                dp(Spacing.lg),
                dp(Spacing.screen_x),
                dp(Spacing.nav_clearance),
            ],
            spacing=dp(Spacing.md),
            size_hint_y=None,
        )
        root.bind(minimum_height=root.setter("height"))

        header = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(44))
        if self._show_back:
            btn = RoundIconButton(icon=Icons.arrow_back, diameter=40)
            btn.bg_color = Colors.surface
            btn.icon_color = Colors.text
            btn.on_press_cb = self._go_back
            header.add_widget(btn)
        header.add_widget(Widget())
        root.add_widget(header)

        title = Label(
            text=self._title,
            font_name=Fonts.bold,
            font_size=dp(28),
            color=Colors.text,
            halign="left",
            valign="middle",
            size_hint_y=None,
            height=dp(40),
        )
        title.bind(size=lambda *_: setattr(title, "text_size", title.size))
        root.add_widget(title)

        card = PastelCard(
            title="Coming in Phase 1",
            subtitle=self._subtitle,
            palette=self._palette,
            size_hint_y=None,
            height=dp(140),
            interactive=False,
        )
        root.add_widget(card)
        root.add_widget(Widget(size_hint_y=None, height=dp(24)))
        scroll.add_widget(root)
        self.add_widget(scroll)
