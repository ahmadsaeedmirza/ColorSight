from colorsight.screens._placeholder import PlaceholderScreen


class PhotosScreen(PlaceholderScreen):
    def __init__(self, **kwargs):
        super().__init__(
            name="photos",
            title="Photos",
            subtitle="Pick an image and apply your correction profile. Coming in Phase 1.",
            palette="pink",
            **kwargs,
        )
