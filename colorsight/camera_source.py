"""Camera capture backends: desktop OpenCV, fake frames, Android Camera4Kivy."""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
import traceback
from typing import Callable

import numpy as np

from colorsight.camera_pipeline import ensure_rgb_uint8
from colorsight.photo_io import is_android

log = logging.getLogger("colorsight")

# Friendly error codes surfaced in the Camera UI (never paths).
ERR_PERMISSION = "permission_denied"
ERR_NO_CAMERA = "no_camera"
ERR_START_FAILED = "start_failed"

FRIENDLY_ERRORS = {
    ERR_PERMISSION: "Camera permission denied",
    ERR_NO_CAMERA: "No camera found",
    ERR_START_FAILED: "Camera failed to start",
}


class CameraSessionState:
    """Testable camera lifecycle (permission → start → stop)."""

    IDLE = "idle"
    PERMISSION_DENIED = "permission_denied"
    NO_CAMERA = "no_camera"
    START_FAILED = "start_failed"
    STARTED = "started"
    STOPPED = "stopped"

    def __init__(self):
        self.state = self.IDLE
        self.error_code: str | None = None

    def reset(self) -> None:
        self.state = self.IDLE
        self.error_code = None

    def on_permission(self, granted: bool) -> None:
        if granted:
            self.state = self.IDLE
            self.error_code = None
            log.info("camera_event permission=granted")
        else:
            self.state = self.PERMISSION_DENIED
            self.error_code = ERR_PERMISSION
            log.warning("camera_event permission=denied")

    def on_start_result(self, ok: bool, reason: str | None = None) -> None:
        if ok:
            self.state = self.STARTED
            self.error_code = None
            log.info("camera_event opened")
            return
        code = reason or ERR_START_FAILED
        if code == ERR_NO_CAMERA:
            self.state = self.NO_CAMERA
        elif code == ERR_PERMISSION:
            self.state = self.PERMISSION_DENIED
        else:
            self.state = self.START_FAILED
            code = ERR_START_FAILED
        self.error_code = code
        log.error("camera_event start_failed reason=%s", code)

    def on_stop(self) -> None:
        self.state = self.STOPPED
        log.info("camera_event stopped")

    def on_first_frame(self, width: int, height: int) -> None:
        log.info("camera_event first_frame size=%sx%s", width, height)

    def friendly_message(self) -> str | None:
        if self.error_code is None:
            return None
        return FRIENDLY_ERRORS.get(self.error_code, FRIENDLY_ERRORS[ERR_START_FAILED])


class FrameSource:
    """Thread-safe latest-frame source (RGB uint8)."""

    is_synthetic: bool = False
    last_error: str | None = None
    frame_size: tuple[int, int] = (0, 0)

    def start(self) -> bool:
        raise NotImplementedError

    def stop(self) -> None:
        raise NotImplementedError

    def read_latest(self) -> np.ndarray | None:
        """Return the newest RGB frame or None (never blocks long)."""
        raise NotImplementedError

    def flip(self) -> None:
        """Flip facing camera when supported (Android)."""

    def attach_host(self, host) -> None:
        """Optional: attach a Preview widget under ``host`` (Android)."""

    @property
    def running(self) -> bool:
        return False


class OpenCVWebcamSource(FrameSource):
    """Desktop webcam via OpenCV VideoCapture."""

    is_synthetic = False

    def __init__(self, index: int = 0):
        self._index = index
        self._cap = None
        self._lock = threading.Lock()
        self._latest: np.ndarray | None = None
        self._running = False
        self._thread: threading.Thread | None = None
        self.last_error: str | None = None
        self.frame_size = (0, 0)

    @property
    def running(self) -> bool:
        return self._running

    def start(self) -> bool:
        if self._running:
            return True
        try:
            import cv2
        except ImportError:
            log.error("camera_event opencv_missing")
            self.last_error = ERR_START_FAILED
            return False
        self._cap = cv2.VideoCapture(self._index)
        if not self._cap.isOpened():
            log.warning("camera_event webcam_open_failed index=%s", self._index)
            self._cap.release()
            self._cap = None
            self.last_error = ERR_NO_CAMERA
            return False
        self._running = True
        self.last_error = None
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        log.info("camera_event webcam_opened index=%s", self._index)
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
            h, w = rgb.shape[:2]
            with self._lock:
                self._latest = rgb  # drop previous — no queue
                self.frame_size = (w, h)
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
        log.info("camera_event webcam_stopped")


class FakeFrameSource(FrameSource):
    """Synthetic frames for desktop smoke tests / webcam fallback only."""

    is_synthetic = True

    def __init__(self, size: tuple[int, int] = (480, 640), fps: float = 20.0):
        self._h, self._w = size
        self._fps = fps
        self._running = False
        self._lock = threading.Lock()
        self._latest: np.ndarray | None = None
        self._thread: threading.Thread | None = None
        self._t0 = 0.0
        self.last_error = None
        self.frame_size = (self._w, self._h)

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
        log.info("camera_event synthetic_started size=%sx%s", self._w, self._h)
        return True

    def _loop(self):
        while self._running:
            t = time.time() - self._t0
            frame = np.zeros((self._h, self._w, 3), dtype=np.uint8)
            shift = int((t * 60) % self._w)
            q = self._w // 4
            cols = [(220, 40, 30), (40, 180, 50), (240, 140, 30), (30, 90, 220)]
            for i, c in enumerate(cols):
                x0 = (i * q + shift) % self._w
                x1 = min(self._w, x0 + q)
                frame[:, x0:x1] = c
                if x0 + q > self._w:
                    frame[:, : (x0 + q) % self._w] = c
            cy, cx = self._h // 2, self._w // 2
            frame[cy - 20 : cy + 20, cx - 2 : cx + 2] = (255, 255, 255)
            frame[cy - 2 : cy + 2, cx - 20 : cx + 20] = (255, 255, 255)
            with self._lock:
                self._latest = frame
                self.frame_size = (self._w, self._h)
            time.sleep(1.0 / max(1.0, self._fps))

    def read_latest(self) -> np.ndarray | None:
        with self._lock:
            return None if self._latest is None else self._latest.copy()

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        log.info("camera_event synthetic_stopped")


class AndroidCameraSource(FrameSource):
    """Android capture via Camera4Kivy Preview + analyze_pixels_callback.

    Decision (see architecture.md): Camera4Kivy + vendored ``camerax_provider``
    is the primary path for p4a 2026.05.09 / Python 3.14 / arm64-v8a. Preview
    stays tiny/invisible; processed frames blit through LivePreviewStage.
    """

    is_synthetic = False

    def __init__(self):
        self._running = False
        self._lock = threading.Lock()
        self._latest: np.ndarray | None = None
        self._facing = "back"
        self._preview = None
        self._host = None
        self._first_frame = False
        self.last_error: str | None = None
        self.frame_size = (0, 0)
        self._on_first_frame: Callable[[int, int], None] | None = None

    @property
    def running(self) -> bool:
        return self._running

    def attach_host(self, host) -> None:
        self._host = host

    def set_first_frame_cb(self, cb: Callable[[int, int], None] | None) -> None:
        self._on_first_frame = cb

    def start(self) -> bool:
        if self._running:
            return True
        try:
            from camera4kivy import Preview  # type: ignore
        except Exception as exc:
            log.error(
                "camera_event camera4kivy_import_failed: %s\n%s",
                exc,
                traceback.format_exc(),
            )
            self.last_error = ERR_START_FAILED
            return False

        try:
            if self._preview is None:
                self._preview = _AnalysisPreview(
                    on_pixels=self._on_pixels,
                    aspect_ratio="16:9",
                )
                # Keep Preview in the tree so CameraX surfaces stay alive, but
                # invisible — we render through LivePreviewStage instead.
                self._preview.size_hint = (None, None)
                self._preview.size = (2, 2)
                self._preview.opacity = 0
                self._preview.pos = (0, 0)
                if self._host is not None:
                    self._host.add_widget(self._preview)
                    log.info("camera_event preview_attached")
                else:
                    log.warning("camera_event preview_no_host")

            facing = self._facing
            self._preview.connect_camera(
                camera_id=facing,
                mirrored=(facing == "front"),
                enable_analyze_pixels=True,
                analyze_pixels_resolution=640,
                enable_video=False,
            )
            self._running = True
            self._first_frame = False
            self.last_error = None
            log.info("camera_event connect_camera facing=%s", facing)
            return True
        except Exception as exc:
            log.error(
                "camera_event connect_failed: %s\n%s", exc, traceback.format_exc()
            )
            msg = str(exc).lower()
            if "permission" in msg:
                self.last_error = ERR_PERMISSION
            elif "camera" in msg and ("not found" in msg or "unavailable" in msg):
                self.last_error = ERR_NO_CAMERA
            else:
                self.last_error = ERR_START_FAILED
            self._running = False
            return False

    def _on_pixels(self, pixels, image_size, mirror: bool) -> None:
        try:
            w, h = int(image_size[0]), int(image_size[1])
            if w <= 0 or h <= 0:
                return
            arr = np.frombuffer(pixels, dtype=np.uint8)
            if arr.size < w * h * 4:
                # Some providers may deliver RGB
                if arr.size >= w * h * 3:
                    rgb = arr[: w * h * 3].reshape((h, w, 3)).copy()
                else:
                    return
            else:
                rgba = arr[: w * h * 4].reshape((h, w, 4))
                rgb = rgba[:, :, :3].copy()
            if mirror:
                rgb = np.ascontiguousarray(np.fliplr(rgb))
            rgb = ensure_rgb_uint8(rgb, from_bgr=False)
            with self._lock:
                self._latest = rgb
                self.frame_size = (w, h)
            if not self._first_frame:
                self._first_frame = True
                log.info("camera_event first_frame size=%sx%s mirror=%s", w, h, mirror)
                if callable(self._on_first_frame):
                    self._on_first_frame(w, h)
        except Exception:
            log.exception("camera_event pixel_callback_failed")

    def push_frame_rgb(self, rgb: np.ndarray) -> None:
        """Test / alternate path: push an RGB frame into the latest slot."""
        try:
            rgb = ensure_rgb_uint8(rgb, from_bgr=False)
        except Exception:
            return
        h, w = rgb.shape[:2]
        with self._lock:
            self._latest = rgb
            self.frame_size = (w, h)

    def read_latest(self) -> np.ndarray | None:
        with self._lock:
            return None if self._latest is None else self._latest.copy()

    def flip(self) -> None:
        self._facing = "front" if self._facing == "back" else "back"
        log.info("camera_event flip facing=%s", self._facing)
        if self._preview is None or not self._running:
            return
        try:
            # Camera4Kivy: 'toggle' or explicit facing id
            self._preview.select_camera("toggle")
        except Exception:
            log.exception("camera_event flip_failed — reconnecting")
            try:
                self._preview.disconnect_camera()
            except Exception:
                pass
            try:
                self._preview.connect_camera(
                    camera_id=self._facing,
                    mirrored=(self._facing == "front"),
                    enable_analyze_pixels=True,
                    analyze_pixels_resolution=640,
                    enable_video=False,
                )
            except Exception:
                log.exception("camera_event flip_reconnect_failed")

    def stop(self) -> None:
        self._running = False
        if self._preview is not None:
            try:
                self._preview.disconnect_camera()
                log.info("camera_event disconnect_camera")
            except Exception:
                log.exception("camera_event disconnect_failed")
            try:
                if self._host is not None and self._preview.parent is self._host:
                    self._host.remove_widget(self._preview)
            except Exception:
                pass
            self._preview = None
        with self._lock:
            self._latest = None
        log.info("camera_event android_stopped")


def _AnalysisPreview_factory():
    """Build Preview subclass only when camera4kivy is importable."""
    from camera4kivy import Preview  # type: ignore

    class AnalysisPreview(Preview):
        def __init__(self, on_pixels=None, **kwargs):
            super().__init__(**kwargs)
            self._on_pixels = on_pixels

        def analyze_pixels_callback(
            self, pixels, image_size, image_pos, scale, mirror
        ):
            cb = self._on_pixels
            if callable(cb):
                cb(pixels, image_size, bool(mirror))

    return AnalysisPreview


# Lazy alias so import of this module does not require camera4kivy on desktop
class _AnalysisPreview:
    """Proxy that constructs the real Preview subclass on first init."""

    def __new__(cls, on_pixels=None, **kwargs):
        Real = _AnalysisPreview_factory()
        return Real(on_pixels=on_pixels, **kwargs)


def open_settings_camera() -> None:
    """Open the OS app settings page (Android) so the user can grant CAMERA."""
    if not is_android():
        return
    try:
        from jnius import autoclass  # type: ignore

        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        activity = PythonActivity.mActivity
        Intent = autoclass("android.content.Intent")
        Settings = autoclass("android.provider.Settings")
        Uri = autoclass("android.net.Uri")
        intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
        uri = Uri.fromParts("package", activity.getPackageName(), None)
        intent.setData(uri)
        activity.startActivity(intent)
        log.info("camera_event open_settings")
    except Exception:
        log.exception("camera_event open_settings_failed")


def request_camera_permission(on_result: Callable[[bool], None] | None = None) -> None:
    """Request CAMERA at runtime on Android; desktop always grants."""
    if not is_android():
        log.info("camera_event permission=granted (desktop)")
        if callable(on_result):
            on_result(True)
        return
    try:
        from android.permissions import (  # type: ignore
            Permission,
            check_permission,
            request_permissions,
        )

        if check_permission(Permission.CAMERA):
            log.info("camera_event permission=already_granted")
            if callable(on_result):
                on_result(True)
            return

        def _cb(_perms, grants):
            ok = bool(grants) and all(bool(g) for g in grants)
            log.info("camera_event permission_result granted=%s", ok)
            if callable(on_result):
                on_result(ok)

        log.info("camera_event permission_requesting")
        request_permissions([Permission.CAMERA], _cb)
    except Exception:
        log.exception("camera_event permission_request_failed")
        if callable(on_result):
            on_result(False)


def create_frame_source(*, prefer_fake: bool = False) -> FrameSource:
    """Create the platform frame source. Never silently fakes on Android."""
    if prefer_fake or os.environ.get("COLORSIGHT_FAKE_CAMERA") == "1":
        if is_android():
            log.warning(
                "camera_event COLORSIGHT_FAKE_CAMERA ignored on Android — real camera required"
            )
        else:
            return FakeFrameSource()
    if is_android():
        return AndroidCameraSource()
    return OpenCVWebcamSource(0)
