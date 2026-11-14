from colorsight.screens._placeholder import PlaceholderScreen


class CameraScreen(PlaceholderScreen):
    def __init__(self, **kwargs):
        super().__init__(
            name="camera",
            title="Camera",
            subtitle="Live camera feed with real-time color correction. Coming in Phase 1.",
            palette="sky",
            **kwargs,
        )
