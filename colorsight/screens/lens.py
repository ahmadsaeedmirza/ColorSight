from colorsight.screens._placeholder import PlaceholderScreen


class LensScreen(PlaceholderScreen):
    def __init__(self, **kwargs):
        super().__init__(
            name="lens",
            title="Magnifier Lens",
            subtitle="A loupe that magnifies and names the color under the sample point.",
            palette="mint",
            **kwargs,
        )
