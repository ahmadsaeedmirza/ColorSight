"""Welcome / onboarding — first run leads to the color test."""

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

from colorsight.prefs import mark_onboarding_done
from colorsight.theme.tokens import Colors, Fonts, Icons, Radii, Spacing
from colorsight.widgets import PastelCard, PrimaryButton, RoundIconButton


class WelcomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(name="welcome", **kwargs)
        self._build()

    def _finish(self, target: str = "test"):
        mark_onboarding_done()
        if self.manager:
            self.manager.transition.direction = "left"
            self.manager.current = target
            parent = self.manager.parent
            if hasattr(parent, "set_nav_active"):
                parent.set_nav_active(target)

    def _build(self):
        scroll = ScrollView(do_scroll_x=False, bar_width=0)
        content = BoxLayout(
            orientation="vertical",
            padding=[
                dp(Spacing.screen_x),
                dp(Spacing.xl),
                dp(Spacing.screen_x),
                dp(Spacing.xl),
            ],
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
            text="See colors more clearly — start with a short\nvision check, then correct photos and live video.",
            font_name=Fonts.regular,
            font_size=dp(15),
            color=Colors.text_muted,
            halign="left",
            valign="top",
            size_hint_y=None,
            height=dp(56),
        )
        subtitle.bind(size=lambda *_: setattr(subtitle, "text_size", subtitle.size))
        content.add_widget(subtitle)

        cta = PrimaryButton(text="Start with the color test")
        cta.on_press_cb = lambda *_: self._finish("test")
        content.add_widget(cta)

        skip_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(56))
        skip_row.add_widget(Widget())
        arrow = RoundIconButton(icon=Icons.arrow_forward, diameter=48)
        arrow.on_press_cb = lambda *_: self._finish("home")
        skip_row.add_widget(arrow)
        content.add_widget(skip_row)

        tip = Label(
            text="You can explore Home anytime — the arrow skips to the toolkit.",
            font_name=Fonts.regular,
            font_size=dp(12),
            color=Colors.text_muted,
            size_hint_y=None,
            height=dp(36),
            halign="left",
        )
        tip.bind(size=lambda *_: setattr(tip, "text_size", tip.size))
        content.add_widget(tip)

        cards = [
            ("Vision Test", "Find your color vision profile", "yellow"),
            ("Photos", "Correct images from your gallery", "pink"),
            ("Live Camera", "Real-time corrected preview", "sky"),
            ("Magnifier Lens", "Zoom in and name the color", "mint"),
        ]
        for title_t, sub, palette in cards:
            content.add_widget(
                PastelCard(
                    title=title_t,
                    subtitle=sub,
                    palette=palette,
                    size_hint_y=None,
                    height=dp(100),
                    radius=Radii.card_lg,
                )
            )

        scroll.add_widget(content)
        self.add_widget(scroll)
