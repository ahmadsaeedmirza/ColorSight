from colorsight.screens._placeholder import PlaceholderScreen


class TestScreen(PlaceholderScreen):
    def __init__(self, **kwargs):
        super().__init__(
            name="test",
            title="Vision Test",
            subtitle="A guided color vision test will live here and build your correction profile.",
            palette="yellow",
            **kwargs,
        )
