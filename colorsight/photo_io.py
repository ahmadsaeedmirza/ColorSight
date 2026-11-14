"""Platform photo pick / save (desktop + Android MediaStore / Photo Picker)."""

from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Callable


def is_android() -> bool:
    return "ANDROID_ARGUMENT" in os.environ or hasattr(sys, "getandroidapilevel")


def pictures_dir() -> Path:
    home = Path.home()
    for name in ("Pictures", "pictures"):
        p = home / name
        if p.is_dir():
            return p
    p = home / "Pictures"
    p.mkdir(parents=True, exist_ok=True)
    return p


def pick_image(on_picked: Callable[[str | None], None], *, on_error: Callable[[str], None] | None = None) -> None:
    """Open a photo picker; callback receives a local file path or None (cancel)."""
    try:
        if is_android():
            _pick_android(on_picked, on_error=on_error)
        else:
            _pick_desktop(on_picked, on_error=on_error)
    except Exception as exc:  # noqa: BLE001
        if on_error:
            on_error(str(exc))
        else:
            on_picked(None)


def _pick_desktop(on_picked: Callable[[str | None], None], *, on_error=None) -> None:
    from kivy.app import App

    try:
        from tkinter import Tk, filedialog
    except Exception as exc:  # noqa: BLE001
        if on_error:
            on_error(f"File chooser unavailable: {exc}")
        on_picked(None)
        return

    def _run(_dt=None):
        root = Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askopenfilename(
            title="Choose a photo",
            filetypes=[
                ("Images", "*.jpg *.jpeg *.png *.webp *.JPG *.JPEG *.PNG *.WEBP"),
                ("All files", "*.*"),
            ],
        )
        root.destroy()
        on_picked(path or None)

    # Defer so Kivy can finish the current frame
    app = App.get_running_app()
    if app is not None:
        from kivy.clock import Clock

        Clock.schedule_once(lambda dt: _run(), 0)
    else:
        _run()


def ensure_read_images_permission() -> bool:
    """Request READ_MEDIA_IMAGES / READ_EXTERNAL_STORAGE on older Android; no-op on desktop.

    Android 13+ Photo Picker does not need this. Returns True if granted or not required.
    """
    if not is_android():
        return True
    try:
        from android.permissions import Permission, check_permission, request_permissions  # type: ignore
        from jnius import autoclass  # type: ignore

        Build = autoclass("android.os.Build")
        sdk = int(Build.VERSION.SDK_INT)
        if sdk >= 33:
            # Photo Picker / partial media access — no broad grant required for picker
            return True
        needed = []
        if sdk >= 33:
            perm = getattr(Permission, "READ_MEDIA_IMAGES", None)
            if perm and not check_permission(perm):
                needed.append(perm)
        else:
            perm = Permission.READ_EXTERNAL_STORAGE
            if not check_permission(perm):
                needed.append(perm)
        if not needed:
            return True
        granted = {"ok": False}

        def _cb(_perms, grants):
            granted["ok"] = all(bool(g) for g in grants)

        request_permissions(needed, _cb)
        return True  # async; picker path still preferred
    except Exception:
        return True


def _pick_android(on_picked: Callable[[str | None], None], *, on_error=None) -> None:
    """Prefer Android Photo Picker; fall back to Intent.ACTION_GET_CONTENT."""
    ensure_read_images_permission()
    try:
        from android import activity, mActivity  # type: ignore
        from jnius import autoclass  # type: ignore

        Intent = autoclass("android.content.Intent")
        Build = autoclass("android.os.Build")

        REQUEST = 0xC501

        def _result(_request, result, intent):
            activity.unbind(on_activity_result=_result)
            if result != -1 or intent is None:  # RESULT_OK = -1
                on_picked(None)
                return
            try:
                uri = intent.getData()
                path = _android_uri_to_tempfile(uri)
                on_picked(path)
            except Exception as exc:  # noqa: BLE001
                if on_error:
                    on_error(str(exc))
                on_picked(None)

        activity.bind(on_activity_result=_result)

        # Photo Picker (API 33+) via ACTION_PICK_IMAGES when available
        intent = None
        try:
            if int(Build.VERSION.SDK_INT) >= 33:
                intent = Intent("android.provider.action.PICK_IMAGES")
                intent.setType("image/*")
        except Exception:
            intent = None
        if intent is None:
            intent = Intent(Intent.ACTION_GET_CONTENT)
            intent.setType("image/*")
            intent.addCategory(Intent.CATEGORY_OPENABLE)

        chooser = Intent.createChooser(intent, "Choose a photo")
        mActivity.startActivityForResult(chooser, REQUEST)
    except Exception as exc:  # noqa: BLE001
        if on_error:
            on_error(str(exc))
        on_picked(None)


def _android_uri_to_tempfile(uri) -> str:
    from android import mActivity  # type: ignore
    from jnius import autoclass  # type: ignore

    ContentResolver = mActivity.getContentResolver()
    stream = ContentResolver.openInputStream(uri)
    ByteArrayOutputStream = autoclass("java.io.ByteArrayOutputStream")
    bos = ByteArrayOutputStream()
    JArray = autoclass("[B")
    jbuf = JArray(8192)
    while True:
        n = stream.read(jbuf)
        if n <= 0:
            break
        bos.write(jbuf, 0, n)
    stream.close()
    data = bytes(bos.toByteArray())
    tmp = Path(tempfile.gettempdir()) / f"colorsight_pick_{datetime.now().strftime('%H%M%S%f')}.jpg"
    tmp.write_bytes(data)
    return str(tmp)


def save_corrected_image(
    rgb,
    *,
    preferred_name: str | None = None,
    fmt: str = "jpg",
) -> str:
    """Save full-res RGB. Returns a friendly label (never a raw path for UI).

    Desktop → Pictures/ColorSight/. Android → MediaStore album ColorSight.
    """
    from colorsight.image_pipeline import encode_image

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = preferred_name or f"ColorSight_{stamp}"
    if not name.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
        name = f"{name}.{'png' if fmt == 'png' else 'jpg'}"

    if is_android():
        return _save_android_mediastore(rgb, name)

    out_dir = pictures_dir() / "ColorSight"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = encode_image(rgb, out_dir / name, quality=95)
    # Friendly confirmation only — caller must not show path
    return "Saved to your gallery"


def _save_android_mediastore(rgb, filename: str) -> str:
    """Insert into MediaStore.Images so it appears in the Gallery (scoped storage)."""
    import tempfile

    from colorsight.image_pipeline import encode_image

    tmp = Path(tempfile.gettempdir()) / filename
    encode_image(rgb, tmp, quality=95)

    try:
        from android import mActivity  # type: ignore
        from jnius import autoclass  # type: ignore

        ContentValues = autoclass("android.content.ContentValues")
        MediaColumns = autoclass("android.provider.MediaStore$MediaColumns")
        Images = autoclass("android.provider.MediaStore$Images$Media")
        FileInputStream = autoclass("java.io.FileInputStream")
        Build = autoclass("android.os.Build")

        values = ContentValues()
        values.put(MediaColumns.DISPLAY_NAME, filename)
        values.put(
            MediaColumns.MIME_TYPE,
            "image/jpeg" if filename.lower().endswith((".jpg", ".jpeg")) else "image/png",
        )
        if int(Build.VERSION.SDK_INT) >= 29:
            values.put(MediaColumns.RELATIVE_PATH, "Pictures/ColorSight")
            values.put(MediaColumns.IS_PENDING, 1)

        resolver = mActivity.getContentResolver()
        uri = resolver.insert(Images.EXTERNAL_CONTENT_URI, values)
        out = resolver.openOutputStream(uri)
        inp = FileInputStream(str(tmp))
        jbuf = autoclass("[B")(8192)
        while True:
            n = inp.read(jbuf)
            if n <= 0:
                break
            out.write(jbuf, 0, n)
        inp.close()
        out.close()

        if int(Build.VERSION.SDK_INT) >= 29:
            values.clear()
            values.put(MediaColumns.IS_PENDING, 0)
            resolver.update(uri, values, None, None)

        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass
        return "Saved to your gallery"
    except Exception:
        # Fallback: private app storage copy (still no path shown)
        from android import mActivity  # type: ignore

        dest = Path(mActivity.getExternalFilesDir(None).getAbsolutePath()) / "ColorSight"
        dest.mkdir(parents=True, exist_ok=True)
        encode_image(rgb, dest / filename, quality=95)
        return "Saved to your gallery"
