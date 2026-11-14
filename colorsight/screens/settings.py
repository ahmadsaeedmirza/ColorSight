from colorsight.screens._placeholder import PlaceholderScreen


class SettingsScreen(PlaceholderScreen):
    def __init__(self, **kwargs):
        super().__init__(
            name="settings",
            title="Settings",
            subtitle="App preferences, accessibility options, and about. Shell only for now.",
            palette="lavender",
            **kwargs,
        )
