"""Home screen with chips and pastel feature grid."""

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse

from colorsight.theme.tokens import Colors, Fonts, Spacing
from colorsight.widgets import ChipRow, PastelCard, PillSearchBar


class _Avatar(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (dp(40), dp(40))
        self.bind(pos=self._draw, size=self._draw)
        self._draw()

    def _draw(self, *_args):
        self.canvas.clear()
        with self.canvas:
            Color(*Colors.accent_blue)
            Ellipse(pos=self.pos, size=self.size)
            Color(1, 1, 1, 1)
            # simple face mark
            r = dp(4)
            Ellipse(pos=(self.center_x - dp(8) - r / 2, self.center_y + dp(2)), size=(r, r))
            Ellipse(pos=(self.center_x + dp(8) - r / 2, self.center_y + dp(2)), size=(r, r))


class _MenuIcon(Label):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.text = "☰"
        self.font_size = dp(22)
        self.color = Colors.text
        self.size_hint = (None, None)
        self.size = (dp(40), dp(40))
        self.halign = "center"
        self.valign = "middle"
        self.bind(size=lambda *_: setattr(self, "text_size", self.size))


class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(name="home", **kwargs)
        self._build()

    def _open(self, screen_name):
        def _handler(_card=None):
            if self.manager:
                self.manager.transition.direction = "left"
                self.manager.current = screen_name
                app = self.get_root_window()
                # notify app nav via screen change; FloatingNavBar syncs in app
                if hasattr(self.manager.parent, "set_nav_active"):
                    self.manager.parent.set_nav_active(screen_name)

        return _handler

    def _on_chip(self, selected: str):
        mapping = {
            "All": None,
            "Test": "test",
            "Photos": "photos",
            "Camera": "camera",
        }
        target = mapping.get(selected)
        if target and self.manager:
            self.manager.current = target

    def _build(self):
        scroll = ScrollView(do_scroll_x=False, bar_width=0)
        content = BoxLayout(
            orientation="vertical",
            padding=[dp(Spacing.screen_x), dp(Spacing.lg), dp(Spacing.screen_x), dp(110)],
            spacing=dp(Spacing.md),
            size_hint_y=None,
        )
        content.bind(minimum_height=content.setter("height"))

        header = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(44),
        )
        header.add_widget(_MenuIcon())
        header.add_widget(Widget())
        header.add_widget(_Avatar())
        content.add_widget(header)

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
        content.add_widget(greet)

        content.add_widget(PillSearchBar(hint="Search features"))

        chips = ChipRow(options=["All", "Test", "Photos", "Camera"], selected="All")
        chips.on_change = self._on_chip
        content.add_widget(chips)

        grid = GridLayout(
            cols=2,
            spacing=dp(Spacing.grid_gap),
            size_hint_y=None,
            height=dp(420),
        )

        features = [
            ("Vision Test", "Ishihara-style check", "yellow", "test", 150),
            ("Photos", "Fix gallery colors", "pink", "photos", 150),
            ("Camera", "Live correction", "sky", "camera", 170),
            ("Lens", "Name that color", "mint", "lens", 170),
            ("Profile", "Your correction", "peach", "profile", 150),
            ("Settings", "Preferences", "lavender", "settings", 150),
        ]
        # two-column: compute total height from rows
        row_h = [150, 170, 150]
        grid.height = dp(sum(row_h) + Spacing.grid_gap * 2)

        for title, sub, palette, screen, h in features:
            card = PastelCard(
                title=title,
                subtitle=sub,
                palette=palette,
                size_hint_y=None,
                height=dp(h),
            )
            card.on_select = self._open(screen)
            grid.add_widget(card)

        content.add_widget(grid)
        scroll.add_widget(content)
        self.add_widget(scroll)
