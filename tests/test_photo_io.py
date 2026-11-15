"""Unit tests for photo_io stream copy + friendly error paths (no Android/JNI)."""

from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from colorsight.photo_io import (
    copy_stream_to_path,
    pick_image,
    save_corrected_image,
    share_image,
)


class TestCopyStreamToPath(unittest.TestCase):
    def test_copies_bytes_to_file(self):
        payload = b"\xff\xd8\xff" + b"JPEGFAKE" * 200
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "out" / "pick.jpg"
            out = copy_stream_to_path(io.BytesIO(payload), dest)
            self.assertEqual(out, dest)
            self.assertTrue(dest.is_file())
            self.assertEqual(dest.read_bytes(), payload)

    def test_empty_stream_raises(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "empty.jpg"
            with self.assertRaises(RuntimeError):
                copy_stream_to_path(io.BytesIO(b""), dest)

    def test_creates_parent_dirs(self):
        payload = b"abc123"
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "a" / "b" / "c.bin"
            copy_stream_to_path(io.BytesIO(payload), dest)
            self.assertEqual(dest.read_bytes(), payload)


class TestPickImageErrorPaths(unittest.TestCase):
    def test_top_level_pick_image_exception_calls_on_error(self):
        errors: list[str] = []
        picked: list = []

        with mock.patch("colorsight.photo_io.is_android", return_value=True):
            with mock.patch(
                "colorsight.photo_io._pick_android",
                side_effect=RuntimeError("boom"),
            ):
                pick_image(
                    lambda p: picked.append(p),
                    on_error=lambda m: errors.append(m),
                )

        self.assertEqual(len(errors), 1)
        self.assertIn("photo picker", errors[0].lower())
        self.assertEqual(picked, [None])
        self.assertNotIn("/", errors[0])
        self.assertNotIn("\\", errors[0])

    def test_desktop_tk_import_error_friendly_message(self):
        errors: list[str] = []
        picked: list = []

        with mock.patch("colorsight.photo_io.is_android", return_value=False):
            # Patch the import inside _pick_desktop by raising on tkinter
            real_import = __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__

            def _blocked(name, *args, **kwargs):
                if name == "tkinter" or name.startswith("tkinter."):
                    raise ImportError("simulated missing tkinter")
                return real_import(name, *args, **kwargs)

            with mock.patch("builtins.__import__", side_effect=_blocked):
                from colorsight import photo_io

                photo_io._pick_desktop(
                    lambda p: picked.append(p),
                    on_error=lambda m: errors.append(m),
                )

        self.assertEqual(picked, [None])
        self.assertEqual(len(errors), 1)
        self.assertIn("chooser", errors[0].lower())
        self.assertNotIn("/", errors[0])

    def test_on_error_none_still_calls_on_picked_none(self):
        picked: list = []
        with mock.patch("colorsight.photo_io.is_android", return_value=True):
            with mock.patch(
                "colorsight.photo_io._pick_android",
                side_effect=RuntimeError("boom"),
            ):
                pick_image(lambda p: picked.append(p), on_error=None)
        self.assertEqual(picked, [None])


class TestAndroidStorage4KivyFallback(unittest.TestCase):
    def test_pick_android_falls_back_when_storage4kivy_missing(self):
        from colorsight import photo_io

        legacy = mock.Mock()
        with mock.patch.object(photo_io, "ensure_read_images_permission"):
            with mock.patch.object(
                photo_io,
                "_pick_android_storage4kivy",
                return_value=False,
            ):
                with mock.patch.object(photo_io, "_pick_android_legacy", legacy):
                    photo_io._pick_android(lambda p: None, on_error=None)
        legacy.assert_called_once()

    def test_storage4kivy_chooser_callback_copies_shared(self):
        from colorsight import photo_io

        picked: list = []
        fake_chooser = mock.Mock()
        fake_ss = mock.Mock()
        fake_ss.copy_from_shared.return_value = "/cache/ColorSightPick/x.jpg"

        class _FakeChooser:
            def __init__(self, cb):
                self._cb = cb

            def choose_content(self, mime):
                self._cb(["content://fake/1"])

        with mock.patch.object(photo_io, "ensure_read_images_permission"):
            with mock.patch.dict(
                "sys.modules",
                {
                    "androidstorage4kivy": mock.Mock(
                        Chooser=_FakeChooser,
                        SharedStorage=lambda: fake_ss,
                    )
                },
            ):
                # Force re-import path inside the function
                ok = photo_io._pick_android_storage4kivy(
                    lambda p: picked.append(p), on_error=None
                )
        self.assertTrue(ok)
        self.assertEqual(picked, ["/cache/ColorSightPick/x.jpg"])
        fake_ss.copy_from_shared.assert_called_once()


class TestSaveShareMessages(unittest.TestCase):
    def test_desktop_save_friendly_label(self):
        rgb = np.zeros((8, 8, 3), dtype=np.uint8)
        rgb[:] = (200, 40, 40)
        with mock.patch("colorsight.photo_io.is_android", return_value=False):
            with tempfile.TemporaryDirectory() as td:
                with mock.patch(
                    "colorsight.photo_io.pictures_dir",
                    return_value=Path(td),
                ):
                    msg = save_corrected_image(rgb, preferred_name="UnitTest", fmt="jpg")
        self.assertEqual(msg, "Saved to your gallery")
        self.assertNotIn("/", msg)
        self.assertNotIn("\\", msg)

    def test_save_failure_raises_friendly_runtime_error(self):
        rgb = np.zeros((4, 4, 3), dtype=np.uint8)
        with mock.patch("colorsight.photo_io.is_android", return_value=False):
            with mock.patch(
                "colorsight.photo_io._save_image_bytes",
                side_effect=OSError("disk full"),
            ):
                with self.assertRaises(RuntimeError) as ctx:
                    save_corrected_image(rgb, preferred_name="Fail", fmt="jpg")
        self.assertIn("Couldn't save", str(ctx.exception))
        self.assertNotIn("/", str(ctx.exception))

    def test_share_desktop_friendly(self):
        rgb = np.zeros((8, 8, 3), dtype=np.uint8)
        done: list[str] = []
        with mock.patch("colorsight.photo_io.is_android", return_value=False):
            with tempfile.TemporaryDirectory() as td:
                with mock.patch(
                    "colorsight.photo_io.pictures_dir",
                    return_value=Path(td),
                ):
                    msg = share_image(
                        rgb,
                        preferred_name="UnitShare",
                        on_done=lambda m: done.append(m),
                    )
        self.assertEqual(msg, "Saved to your gallery")
        self.assertEqual(done, ["Saved to your gallery"])

    def test_share_android_failure_fallback_message(self):
        rgb = np.zeros((4, 4, 3), dtype=np.uint8)
        with mock.patch("colorsight.photo_io.is_android", return_value=True):
            with mock.patch(
                "colorsight.photo_io._save_image_bytes",
                return_value=Path("share.jpg"),
            ):
                with mock.patch(
                    "colorsight.photo_io._share_android",
                    side_effect=RuntimeError("no provider"),
                ):
                    msg = share_image(rgb, preferred_name="ShareFail")
        self.assertIn("gallery", msg.lower())
        self.assertNotIn("/", msg)


class TestFileProviderHookSnippet(unittest.TestCase):
    def test_hook_injects_provider_before_application_close(self):
        # Lightweight check that the hook module's snippet shape is sane
        from pathlib import Path
        import importlib.util

        hook_path = (
            Path(__file__).resolve().parents[1]
            / "assets"
            / "android"
            / "p4a_fileprovider_hook.py"
        )
        spec = importlib.util.spec_from_file_location("p4a_fp_hook", hook_path)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)

        fake = (
            '<?xml version="1.0"?>\n'
            '<manifest package="org.colorsight.colorsight">\n'
            "    <application>\n"
            "        <activity android:name=\".Main\"/>\n"
            "    </application>\n"
            "</manifest>\n"
        )
        with tempfile.TemporaryDirectory() as td:
            dist = Path(td)
            man = dist / "src" / "main" / "AndroidManifest.xml"
            man.parent.mkdir(parents=True)
            man.write_text(fake, encoding="utf-8")
            # Also place sibling file_paths for ensure helper
            paths_src = hook_path.parent / "file_paths.xml"
            self.assertTrue(paths_src.is_file())

            class _Dist:
                dist_dir = str(dist)
                package_name = "org.colorsight.colorsight"

            class _TC:
                _dist = _Dist()

            mod.after_apk_build(_TC())
            out = man.read_text(encoding="utf-8")
            self.assertIn("androidx.core.content.FileProvider", out)
            self.assertIn("org.colorsight.colorsight.fileprovider", out)
            self.assertIn("@xml/file_paths", out)
            self.assertTrue((dist / "src" / "main" / "res" / "xml" / "file_paths.xml").is_file())


if __name__ == "__main__":
    unittest.main()
