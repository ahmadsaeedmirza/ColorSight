"""Unit tests for camera frame helpers + CameraSessionState (no Android/JNI)."""

from __future__ import annotations

import unittest
from unittest import mock

import numpy as np

from colorsight.camera_source import (
    ERR_NO_CAMERA,
    ERR_PERMISSION,
    ERR_START_FAILED,
    FRIENDLY_ERRORS,
    AndroidCameraSource,
    CameraSessionState,
    FakeFrameSource,
    OpenCVWebcamSource,
    create_frame_source,
)


class TestCameraSessionState(unittest.TestCase):
    def test_permission_denied(self):
        s = CameraSessionState()
        s.on_permission(False)
        self.assertEqual(s.state, CameraSessionState.PERMISSION_DENIED)
        self.assertEqual(s.error_code, ERR_PERMISSION)
        self.assertEqual(s.friendly_message(), FRIENDLY_ERRORS[ERR_PERMISSION])

    def test_permission_granted_clears_error(self):
        s = CameraSessionState()
        s.on_permission(False)
        s.on_permission(True)
        self.assertEqual(s.state, CameraSessionState.IDLE)
        self.assertIsNone(s.friendly_message())

    def test_start_ok(self):
        s = CameraSessionState()
        s.on_permission(True)
        s.on_start_result(True)
        self.assertEqual(s.state, CameraSessionState.STARTED)
        self.assertIsNone(s.friendly_message())

    def test_start_no_camera(self):
        s = CameraSessionState()
        s.on_start_result(False, ERR_NO_CAMERA)
        self.assertEqual(s.state, CameraSessionState.NO_CAMERA)
        self.assertEqual(s.friendly_message(), "No camera found")

    def test_start_failed(self):
        s = CameraSessionState()
        s.on_start_result(False, ERR_START_FAILED)
        self.assertEqual(s.state, CameraSessionState.START_FAILED)
        self.assertEqual(s.friendly_message(), "Camera failed to start")

    def test_stop(self):
        s = CameraSessionState()
        s.on_start_result(True)
        s.on_stop()
        self.assertEqual(s.state, CameraSessionState.STOPPED)

    def test_reset(self):
        s = CameraSessionState()
        s.on_permission(False)
        s.reset()
        self.assertEqual(s.state, CameraSessionState.IDLE)
        self.assertIsNone(s.error_code)


class TestFakeFrameSource(unittest.TestCase):
    def test_synthetic_flag_and_frames(self):
        src = FakeFrameSource(size=(40, 60), fps=50.0)
        self.assertTrue(src.is_synthetic)
        self.assertTrue(src.start())
        # Wait briefly for a frame
        import time

        deadline = time.time() + 1.0
        frame = None
        while time.time() < deadline:
            frame = src.read_latest()
            if frame is not None:
                break
            time.sleep(0.02)
        self.assertIsNotNone(frame)
        self.assertEqual(frame.shape, (40, 60, 3))
        self.assertEqual(src.frame_size, (60, 40))
        src.stop()
        self.assertFalse(src.running)


class TestAndroidCameraSourcePush(unittest.TestCase):
    def test_push_and_read(self):
        src = AndroidCameraSource()
        rgb = np.zeros((24, 32, 3), dtype=np.uint8)
        rgb[:] = (10, 20, 30)
        src.push_frame_rgb(rgb)
        out = src.read_latest()
        self.assertIsNotNone(out)
        self.assertEqual(out.shape, (24, 32, 3))
        self.assertEqual(tuple(out[0, 0]), (10, 20, 30))
        self.assertEqual(src.frame_size, (32, 24))

    def test_stop_clears(self):
        src = AndroidCameraSource()
        src.push_frame_rgb(np.ones((8, 8, 3), dtype=np.uint8))
        src.stop()
        self.assertIsNone(src.read_latest())


class TestCreateFrameSource(unittest.TestCase):
    def test_android_never_returns_fake_from_env(self):
        with mock.patch("colorsight.camera_source.is_android", return_value=True):
            with mock.patch.dict("os.environ", {"COLORSIGHT_FAKE_CAMERA": "1"}):
                src = create_frame_source()
        self.assertIsInstance(src, AndroidCameraSource)
        self.assertFalse(src.is_synthetic)

    def test_desktop_fake_env(self):
        with mock.patch("colorsight.camera_source.is_android", return_value=False):
            with mock.patch.dict("os.environ", {"COLORSIGHT_FAKE_CAMERA": "1"}):
                src = create_frame_source()
        self.assertIsInstance(src, FakeFrameSource)

    def test_desktop_default_opencv(self):
        with mock.patch("colorsight.camera_source.is_android", return_value=False):
            with mock.patch.dict("os.environ", {}, clear=False):
                # Ensure env flag off
                import os

                os.environ.pop("COLORSIGHT_FAKE_CAMERA", None)
                src = create_frame_source()
        self.assertIsInstance(src, OpenCVWebcamSource)


class TestFriendlyErrorsHaveNoPaths(unittest.TestCase):
    def test_messages(self):
        for msg in FRIENDLY_ERRORS.values():
            self.assertNotIn("/", msg)
            self.assertNotIn("\\", msg)
            self.assertTrue(len(msg) > 0)


if __name__ == "__main__":
    unittest.main()
