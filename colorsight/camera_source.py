"""Camera capture backends: desktop OpenCV, fake frames, Android Camera4Kivy stub."""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from typing import Callable

import numpy as np

from colorsight.camera_pipeline import ensure_rgb_uint8
from colorsight.photo_io import is_android

log = logging.getLogger(__name__)


class FrameSource:
    """Thread-safe latest-frame source (RGB uint8)."""

    def start(self) -> bool:
        raise NotImplementedError

    def stop(self) -> None:
        raise NotImplementedError

    def read_latest(self) -> np.ndarray | None:
        """Return the newest RGB frame or None (never blocks long)."""
        raise NotImplementedError

    def flip(self) -> None:
        """Flip facing camera when supported (Android)."""

    @property
    def running(self) -> bool:
        return False


class OpenCVWebcamSource(FrameSource):
    """Desktop webcam via OpenCV VideoCapture."""

    def __init__(self, index: int = 0):
        self._index = index
        self._cap = None
        self._lock = threading.Lock()
        self._latest: np.ndarray | None = None
        self._running = False
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self._running

    def start(self) -> bool:
        if self._running:
            return True
        try:
            import cv2
        except ImportError:
            log.error("OpenCV not available")
            return False
        self._cap = cv2.VideoCapture(self._index)
        if not self._cap.isOpened():
            log.warning("Webcam index %s failed to open", self._index)
            self._cap.release()
            self._cap = None
            return False
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return True

    def _loop(self):
        import cv2

        while self._running and self._cap is not None:
            ok, bgr = self._cap.read()
            if not ok or bgr is None:
                time.sleep(0.03)
                continue
            try:
                rgb = ensure_rgb_uint8(bgr, from_bgr=True)
            except Exception:
                continue
            with self._lock:
                self._latest = rgb  # drop previous — no queue
            time.sleep(0.001)

    def read_latest(self) -> np.ndarray | None:
        with self._lock:
            if self._latest is None:
                return None
            return self._latest.copy()

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None
        with self._lock:
            self._latest = None


class FakeFrameSource(FrameSource):
    """Synthetic frames for desktop smoke tests (no webcam required)."""

    def __init__(self, size: tuple[int, int] = (480, 640), fps: float = 20.0):
        self._h, self._w = size
        self._fps = fps
        self._running = False
        self._lock = threading.Lock()
        self._latest: np.ndarray | None = None
        self._thread: threading.Thread | None = None
        self._t0 = 0.0

    @property
    def running(self) -> bool:
        return self._running

    def start(self) -> bool:
        if self._running:
            return True
        self._running = True
        self._t0 = time.time()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return True

    def _loop(self):
        while self._running:
            t = time.time() - self._t0
            frame = np.zeros((self._h, self._w, 3), dtype=np.uint8)
            # Moving color bars
            shift = int((t * 60) % self._w)
            q = self._w // 4
            cols = [(220, 40, 30), (40, 180, 50), (240, 140, 30), (30, 90, 220)]
            for i, c in enumerate(cols):
                x0 = (i * q + shift) % self._w
                x1 = min(self._w, x0 + q)
                frame[:, x0:x1] = c
                if x0 + q > self._w:
                    frame[:, : (x0 + q) % self._w] = c
            # Crosshair target
            cy, cx = self._h // 2, self._w // 2
            frame[cy - 20 : cy + 20, cx - 2 : cx + 2] = (255, 255, 255)
            frame[cy - 2 : cy + 2, cx - 20 : cx + 20] = (255, 255, 255)
            with self._lock:
                self._latest = frame
            time.sleep(1.0 / max(1.0, self._fps))

    def read_latest(self) -> np.ndarray | None:
        with self._lock:
            return None if self._latest is None else self._latest.copy()

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None


class AndroidCameraSource(FrameSource):
    """Android capture via Camera4Kivy when available; otherwise fails gracefully."""

    def __init__(self):
        self._running = False
        self._lock = threading.Lock()
        self._latest: np.ndarray | None = None
        self._facing = "back"
        self._provider = None

    @property
    def running(self) -> bool:
        return self._running

    def start(self) -> bool:
        if self._running:
            return True
        try:
            # Optional dependency — documented in production.md
            from camera4kivy import Preview  # type: ignore

            # Preview widget is UI-bound; we only signal availability here.
            # The Camera screen attaches Preview when on Android.
            self._provider = "camera4kivy"
            self._running = True
            return True
        except Exception as exc:
            log.warning("Android camera backend unavailable: %s", exc)
            return False

    def push_frame_rgb(self, rgb: np.ndarray) -> None:
        """Called by the Camera4Kivy preview callback with RGB frames."""
        try:
            rgb = ensure_rgb_uint8(rgb, from_bgr=False)
        except Exception:
            return
        with self._lock:
            self._latest = rgb

    def read_latest(self) -> np.ndarray | None:
        with self._lock:
            return None if self._latest is None else self._latest.copy()

    def flip(self) -> None:
        self._facing = "front" if self._facing == "back" else "back"

    def stop(self) -> None:
        self._running = False
        with self._lock:
            self._latest = None


def open_settings_camera() -> None:
    """Open the OS app settings page (Android) so the user can grant CAMERA."""
    if not is_android():
        return
    try:
        from android import mActivity  # type: ignore
        from jnius import autoclass  # type: ignore

        Intent = autoclass("android.content.Intent")
        Settings = autoclass("android.provider.Settings")
        Uri = autoclass("android.net.Uri")
        intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
        uri = Uri.fromParts("package", mActivity.getPackageName(), None)
        intent.setData(uri)
        mActivity.startActivity(intent)
    except Exception:
        log.exception("open settings failed")


def request_camera_permission(on_result: Callable[[bool], None] | None = None) -> None:
    """Request CAMERA at runtime on Android; desktop always grants."""
    if not is_android():
        if callable(on_result):
            on_result(True)
        return
    try:
        from android.permissions import Permission, check_permission, request_permissions  # type: ignore

        if check_permission(Permission.CAMERA):
            if callable(on_result):
                on_result(True)
            return

        def _cb(_perms, grants):
            ok = bool(grants) and all(bool(g) for g in grants)
            if callable(on_result):
                on_result(ok)

        request_permissions([Permission.CAMERA], _cb)
    except Exception:
        if callable(on_result):
            on_result(False)


def create_frame_source(*, prefer_fake: bool = False) -> FrameSource:
    if prefer_fake or os.environ.get("COLORSIGHT_FAKE_CAMERA") == "1":
        return FakeFrameSource()
    if is_android():
        return AndroidCameraSource()
    return OpenCVWebcamSource(0)
