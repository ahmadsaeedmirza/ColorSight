"""Clipboard helper — desktop path + truncation (no Android/JNI)."""

from __future__ import annotations

import unittest
from unittest import mock


class TestClipboardUtil(unittest.TestCase):
    def test_desktop_copy_ok(self):
        from colorsight import clipboard_util

        with mock.patch.object(clipboard_util, "is_android", return_value=False):
            with mock.patch.object(clipboard_util, "_win32_copy", return_value=False):
                with mock.patch.object(clipboard_util, "_tk_copy", return_value=False):
                    fake_clip = mock.Mock()
                    fake_clip.copy = mock.Mock()
                    fake_clip.paste = mock.Mock(return_value="hello")
                    fake_mod = mock.Mock(Clipboard=fake_clip)
                    with mock.patch.dict(
                        "sys.modules", {"kivy.core.clipboard": fake_mod}
                    ):
                        self.assertTrue(clipboard_util.copy_text("hello"))
                        fake_clip.copy.assert_called_once_with("hello")

    def test_win32_preferred_on_windows(self):
        from colorsight import clipboard_util

        with mock.patch.object(clipboard_util, "is_android", return_value=False):
            with mock.patch.object(clipboard_util.sys, "platform", "win32"):
                with mock.patch.object(
                    clipboard_util, "_win32_copy", return_value=True
                ) as w:
                    with mock.patch.object(
                        clipboard_util, "_kivy_copy", return_value=False
                    ) as k:
                        self.assertTrue(clipboard_util.copy_text("hi"))
                        w.assert_called_once()
                        k.assert_not_called()

    def test_truncates_huge_text(self):
        from colorsight import clipboard_util

        huge = "x" * (clipboard_util._MAX_CHARS + 5000)
        with mock.patch.object(clipboard_util, "is_android", return_value=False):
            with mock.patch.object(clipboard_util, "_win32_copy", return_value=False):
                with mock.patch.object(clipboard_util, "_tk_copy", return_value=False):
                    fake_clip = mock.Mock()
                    fake_clip.copy = mock.Mock()
                    fake_clip.paste = mock.Mock(return_value="x")
                    fake_mod = mock.Mock(Clipboard=fake_clip)
                    with mock.patch.dict(
                        "sys.modules", {"kivy.core.clipboard": fake_mod}
                    ):
                        self.assertTrue(clipboard_util.copy_text(huge))
                        args = fake_clip.copy.call_args[0][0]
                        self.assertLessEqual(
                            len(args), clipboard_util._MAX_CHARS + 20
                        )
                        self.assertIn("truncated", args)

    def test_copy_failure_returns_false(self):
        from colorsight import clipboard_util

        with mock.patch.object(clipboard_util, "is_android", return_value=False):
            with mock.patch.object(clipboard_util, "_win32_copy", return_value=False):
                with mock.patch.object(clipboard_util, "_tk_copy", return_value=False):
                    with mock.patch.object(
                        clipboard_util, "_kivy_copy", return_value=False
                    ):
                        self.assertFalse(clipboard_util.copy_text("x"))


if __name__ == "__main__":
    unittest.main()
