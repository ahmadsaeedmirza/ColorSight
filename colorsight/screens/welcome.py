"""Welcome / onboarding-style first screen."""

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

from colorsight.theme.tokens import Colors, Fonts, Radii, Spacing
from colorsight.widgets import PastelCard, RoundIconButton


class WelcomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(name="welcome", **kwargs)
        self._build()

    def _go_home(self, *_args):
        if self.manager:
            self.manager.transition.direction = "left"
            self.manager.current = "home"

    def _open(self, screen_name):
        def _handler(_card=None):
            if self.manager:
                self.manager.transition.direction = "left"
                self.manager.current = screen_name

        return _handler

    def _build(self):
        scroll = ScrollView(do_scroll_x=False, bar_width=0)
        content = BoxLayout(
            orientation="vertical",
            padding=[dp(Spacing.screen_x), dp(Spacing.xl), dp(Spacing.screen_x), dp(Spacing.xl)],
            spacing=dp(Spacing.md),
            size_hint_y=None,
        )
        content.bind(minimum_height=content.setter("height"))

        content.add_widget(Widget(size_hint_y=None, height=dp(12)))

        title = Label(
            text="ColorSight",
            font_name=Fonts.bold,
            font_size=dp(40),
            color=Colors.text,
            halign="left",
            valign="middle",
            size_hint_y=None,
            height=dp(52),
        )
        title.bind(size=lambda *_: setattr(title, "text_size", title.size))
        content.add_widget(title)

        subtitle = Label(
            text="See colors more clearly — test, correct,\nand explore with a friendly toolkit.",
            font_name=Fonts.regular,
            font_size=dp(15),
            color=Colors.text_muted,
            halign="left",
            valign="top",
            size_hint_y=None,
            height=dp(52),
        )
        subtitle.bind(size=lambda *_: setattr(subtitle, "text_size", subtitle.size))
        content.add_widget(subtitle)

        cta_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(64),
            spacing=dp(Spacing.md),
        )
        cta_row.add_widget(Widget())
        arrow = RoundIconButton(icon="→", diameter=56)
        arrow.on_press_cb = self._go_home
        cta_row.add_widget(arrow)
        content.add_widget(cta_row)

        content.add_widget(Widget(size_hint_y=None, height=dp(8)))

        cards = [
            ("Vision Test", "Find your color vision profile", "yellow", "test"),
            ("Photos", "Correct images from your gallery", "pink", "photos"),
            ("Live Camera", "Real-time corrected preview", "sky", "camera"),
            ("Magnifier Lens", "Zoom in and name the color", "mint", "lens"),
        ]
        for title_t, sub, palette, screen in cards:
            card = PastelCard(
                title=title_t,
                subtitle=sub,
                palette=palette,
                size_hint_y=None,
                height=dp(110),
                radius=Radii.card_lg,
            )
            card.on_select = self._open(screen)
            content.add_widget(card)

        scroll.add_widget(content)
        self.add_widget(scroll)
