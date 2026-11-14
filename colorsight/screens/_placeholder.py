"""Shared placeholder layout for feature screens."""

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget

from colorsight.theme.tokens import Colors, Fonts, Spacing
from colorsight.widgets import PastelCard


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

    def _build(self):
        root = BoxLayout(
            orientation="vertical",
            padding=[dp(Spacing.screen_x), dp(Spacing.lg), dp(Spacing.screen_x), dp(100)],
            spacing=dp(Spacing.md),
        )

        header = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(40))
        if self._show_back:
            back = Label(
                text="‹ Back",
                font_name=Fonts.medium,
                font_size=dp(16),
                color=Colors.text,
                halign="left",
                valign="middle",
                size_hint_x=None,
                width=dp(90),
            )
            back.bind(size=lambda *_: setattr(back, "text_size", back.size))

            def _go_back(*_a):
                if self.manager:
                    self.manager.current = "home"

            # tap via ButtonBehavior would be better; use a PastelCard-less simple approach
            from colorsight.widgets.primary_button import RoundIconButton

            btn = RoundIconButton(icon="‹", diameter=40)
            btn.bg_color = Colors.surface
            btn.icon_color = Colors.text
            btn.on_press_cb = lambda *_: _go_back()
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
        root.add_widget(Widget())
        self.add_widget(root)
