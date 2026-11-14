from colorsight.screens._placeholder import PlaceholderScreen


class ProfileScreen(PlaceholderScreen):
    def __init__(self, **kwargs):
        super().__init__(
            name="profile",
            title="Profile",
            subtitle="Your saved correction profile from the vision test will appear here.",
            palette="peach",
            **kwargs,
        )
