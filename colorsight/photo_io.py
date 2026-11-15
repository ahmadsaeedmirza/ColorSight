"""Platform photo pick / save / share (desktop + Android Photo Picker / MediaStore)."""

from __future__ import annotations

import logging
import os
import sys
import tempfile
import traceback
from datetime import datetime
from pathlib import Path
from typing import BinaryIO, Callable

log = logging.getLogger("colorsight")

# Activity request codes
_REQ_PICK = 0xC501


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


def _ui(cb: Callable, *args) -> None:
    """Marshal callbacks onto the Kivy main thread when an app is running."""
    try:
        from kivy.app import App
        from kivy.clock import Clock

        if App.get_running_app() is not None:
            Clock.schedule_once(lambda _dt: cb(*args), 0)
            return
    except Exception:
        pass
    cb(*args)


def _log_exc(msg: str, exc: BaseException | None = None) -> None:
    if exc is not None:
        log.error("%s: %s\n%s", msg, exc, traceback.format_exc())
    else:
        log.error("%s\n%s", msg, traceback.format_exc())


def pick_image(
    on_picked: Callable[[str | None], None],
    *,
    on_error: Callable[[str], None] | None = None,
) -> None:
    """Open a photo picker; callback receives a local file path or None (cancel)."""
    try:
        if is_android():
            _pick_android(on_picked, on_error=on_error)
        else:
            _pick_desktop(on_picked, on_error=on_error)
    except Exception as exc:  # noqa: BLE001
        _log_exc("pick_image failed", exc)
        friendly = "Couldn't open the photo picker. Try again."
        if callable(on_error):
            _ui(on_error, friendly)
        _ui(on_picked, None)


def _pick_desktop(
    on_picked: Callable[[str | None], None], *, on_error=None
) -> None:
    try:
        from tkinter import Tk, filedialog
    except Exception as exc:  # noqa: BLE001
        _log_exc("tkinter file chooser unavailable", exc)
        if callable(on_error):
            _ui(on_error, "File chooser unavailable on this device.")
        _ui(on_picked, None)
        return

    def _run(_dt=None):
        try:
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
            _ui(on_picked, path or None)
        except Exception as exc:  # noqa: BLE001
            _log_exc("desktop pick failed", exc)
            if callable(on_error):
                _ui(on_error, "Couldn't open the photo picker.")
            _ui(on_picked, None)

    _ui(_run)


def ensure_read_images_permission() -> bool:
    """Request storage permission on older Android; Photo Picker (13+) needs none."""
    if not is_android():
        return True
    try:
        from android.permissions import (  # type: ignore
            Permission,
            check_permission,
            request_permissions,
        )
        from jnius import autoclass  # type: ignore

        Build = autoclass("android.os.Build")
        sdk = int(Build.VERSION.SDK_INT)
        if sdk >= 33:
            return True
        perm = Permission.READ_EXTERNAL_STORAGE
        if check_permission(perm):
            return True
        request_permissions([perm])
        return True
    except Exception as exc:
        log.warning("permission probe failed: %s", exc)
        return True


def _android_activity():
    """PythonActivity.mActivity — preferred over legacy android.mActivity."""
    from jnius import autoclass  # type: ignore

    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    act = PythonActivity.mActivity
    if act is None:
        raise RuntimeError("Android activity is not ready yet")
    return act


def _pick_android(
    on_picked: Callable[[str | None], None], *, on_error=None
) -> None:
    """Photo Picker (API 33+) via startActivityForResult; else ACTION_GET_CONTENT."""
    ensure_read_images_permission()
    try:
        from android.activity import bind as activity_bind  # type: ignore
        from android.activity import unbind as activity_unbind  # type: ignore
        from jnius import autoclass  # type: ignore

        Intent = autoclass("android.content.Intent")
        Build = autoclass("android.os.Build")
        MediaStore = autoclass("android.provider.MediaStore")
        activity = _android_activity()
        sdk = int(Build.VERSION.SDK_INT)

        def _result(request_code, result_code, intent):
            try:
                activity_unbind(on_activity_result=_result)
            except Exception:
                pass
            RESULT_OK = -1
            if int(request_code) != _REQ_PICK:
                return
            if int(result_code) != RESULT_OK or intent is None:
                log.info("photo pick cancelled or empty result")
                _ui(on_picked, None)
                return
            try:
                uri = intent.getData()
                if uri is None:
                    # Some pickers put URI in clip data
                    clip = intent.getClipData()
                    if clip is not None and clip.getItemCount() > 0:
                        uri = clip.getItemAt(0).getUri()
                if uri is None:
                    raise RuntimeError("No image was returned")
                path = _android_uri_to_tempfile(uri)
                log.info("photo pick ok")
                _ui(on_picked, path)
            except Exception as exc:  # noqa: BLE001
                _log_exc("photo pick result failed", exc)
                if callable(on_error):
                    _ui(on_error, "Couldn't read that photo. Try another one.")
                _ui(on_picked, None)

        activity_bind(on_activity_result=_result)

        intent = None
        used_picker = False
        if sdk >= 33:
            try:
                # Direct Photo Picker — do NOT wrap in createChooser
                action = getattr(
                    MediaStore,
                    "ACTION_PICK_IMAGES",
                    "android.provider.action.PICK_IMAGES",
                )
                intent = Intent(action)
                intent.setType("image/*")
                used_picker = True
            except Exception as exc:
                log.warning("ACTION_PICK_IMAGES unavailable: %s", exc)
                intent = None

        if intent is None:
            intent = Intent(Intent.ACTION_GET_CONTENT)
            intent.setType("image/*")
            intent.addCategory(Intent.CATEGORY_OPENABLE)
            intent = Intent.createChooser(intent, "Choose a photo")
            used_picker = False

        log.info(
            "starting photo pick sdk=%s photo_picker=%s", sdk, used_picker
        )
        activity.startActivityForResult(intent, _REQ_PICK)
    except Exception as exc:  # noqa: BLE001
        _log_exc("android pick launch failed", exc)
        if callable(on_error):
            _ui(on_error, "Couldn't open the photo picker. Try again.")
        _ui(on_picked, None)


def copy_stream_to_path(stream: BinaryIO, dest: Path, *, chunk: int = 65536) -> Path:
    """Copy a file-like binary stream to ``dest`` (testable helper)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as out:
        while True:
            block = stream.read(chunk)
            if not block:
                break
            out.write(block)
    if not dest.is_file() or dest.stat().st_size <= 0:
        raise RuntimeError("Copied image was empty")
    return dest


def _android_cache_dir(*parts: str) -> Path:
    """App cache directory (FileProvider cache-path root)."""
    activity = _android_activity()
    base = Path(activity.getCacheDir().getAbsolutePath())
    path = base.joinpath(*parts) if parts else base
    path.mkdir(parents=True, exist_ok=True)
    return path


def _android_uri_to_tempfile(uri) -> str:
    """content:// → temp file under app cache via ContentResolver.openInputStream."""
    from jnius import autoclass  # type: ignore

    activity = _android_activity()
    resolver = activity.getContentResolver()
    stream = resolver.openInputStream(uri)
    if stream is None:
        raise RuntimeError("Could not open that image")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    dest = _android_cache_dir("ColorSightPick") / f"pick_{stamp}.jpg"

    # Copy Java InputStream → file with FileOutputStream (reliable on pyjnius)
    FileOutputStream = autoclass("java.io.FileOutputStream")
    fos = FileOutputStream(str(dest))
    try:
        buf = autoclass("[B")(8192)
        while True:
            n = stream.read(buf)
            if n < 0:
                break
            if n == 0:
                continue
            fos.write(buf, 0, n)
    finally:
        try:
            stream.close()
        except Exception:
            pass
        try:
            fos.close()
        except Exception:
            pass

    if not dest.is_file() or dest.stat().st_size <= 0:
        raise RuntimeError("Could not copy that image")
    return str(dest)


def save_corrected_image(
    rgb,
    *,
    preferred_name: str | None = None,
    fmt: str = "jpg",
) -> str:
    """Save full-res RGB. Returns friendly label (never a raw path for UI)."""
    try:
        _save_image_bytes(rgb, preferred_name=preferred_name, fmt=fmt)
        log.info("save_corrected_image ok")
        return "Saved to your gallery"
    except Exception as exc:  # noqa: BLE001
        _log_exc("save_corrected_image failed", exc)
        raise RuntimeError("Couldn't save the image. Try again.") from exc


def _normalize_filename(preferred_name: str | None, fmt: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = preferred_name or f"ColorSight_{stamp}"
    if not name.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
        name = f"{name}.{'png' if fmt == 'png' else 'jpg'}"
    return name


def _save_image_bytes(rgb, *, preferred_name: str | None = None, fmt: str = "jpg") -> Path:
    """Write image; returns local Path under FileProvider-visible cache on Android."""
    from colorsight.image_pipeline import encode_image

    name = _normalize_filename(preferred_name, fmt)
    if is_android():
        _save_android_mediastore(rgb, name)
        cache = _android_cache_dir("ColorSightShare")
        return encode_image(rgb, cache / name, quality=95)

    out_dir = pictures_dir() / "ColorSight"
    out_dir.mkdir(parents=True, exist_ok=True)
    return encode_image(rgb, out_dir / name, quality=95)


def share_image(
    rgb,
    *,
    preferred_name: str | None = None,
    fmt: str = "jpg",
    on_done: Callable[[str], None] | None = None,
) -> str:
    """Share via Android ACTION_SEND + FileProvider, or desktop save + confirm."""
    try:
        path = _save_image_bytes(rgb, preferred_name=preferred_name, fmt=fmt)
    except Exception as exc:  # noqa: BLE001
        _log_exc("share_image save failed", exc)
        msg = "Couldn't prepare the image to share."
        if callable(on_done):
            on_done(msg)
        return msg

    if is_android():
        try:
            _share_android(path)
            msg = "Share sheet opened"
            log.info("share_android ok")
        except Exception as exc:  # noqa: BLE001
            _log_exc("share_android failed", exc)
            msg = "Saved to your gallery (share unavailable)"
    else:
        msg = "Saved to your gallery"
    if callable(on_done):
        on_done(msg)
    return msg


def _share_android(path: Path) -> None:
    """Intent.ACTION_SEND with FileProvider content:// URI + FLAG_GRANT_READ_URI_PERMISSION."""
    from jnius import autoclass, cast  # type: ignore

    activity = _android_activity()
    Intent = autoclass("android.content.Intent")
    File = autoclass("java.io.File")
    try:
        FileProvider = autoclass("androidx.core.content.FileProvider")
    except Exception:
        FileProvider = autoclass("android.support.v4.content.FileProvider")

    authority = activity.getPackageName() + ".fileprovider"
    jfile = File(str(path))
    if not jfile.exists():
        raise FileNotFoundError(f"share file missing: {path.name}")
    uri = FileProvider.getUriForFile(activity, authority, jfile)
    intent = Intent(Intent.ACTION_SEND)
    mime = (
        "image/jpeg"
        if path.suffix.lower() in (".jpg", ".jpeg")
        else "image/png"
    )
    intent.setType(mime)
    intent.putExtra(Intent.EXTRA_STREAM, cast("android.os.Parcelable", uri))
    intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    chooser = Intent.createChooser(intent, "Share with ColorSight")
    activity.startActivity(chooser)


def _save_android_mediastore(rgb, filename: str) -> str:
    """Insert into MediaStore.Images (RELATIVE_PATH=Pictures/ColorSight on API 29+)."""
    from colorsight.image_pipeline import encode_image
    from jnius import autoclass  # type: ignore

    tmp_dir = _android_cache_dir("ColorSightMedia")
    tmp = tmp_dir / filename
    encode_image(rgb, tmp, quality=95)

    try:
        activity = _android_activity()
        ContentValues = autoclass("android.content.ContentValues")
        MediaColumns = autoclass("android.provider.MediaStore$MediaColumns")
        Images = autoclass("android.provider.MediaStore$Images$Media")
        FileInputStream = autoclass("java.io.FileInputStream")
        Build = autoclass("android.os.Build")

        values = ContentValues()
        values.put(MediaColumns.DISPLAY_NAME, filename)
        values.put(
            MediaColumns.MIME_TYPE,
            "image/jpeg"
            if filename.lower().endswith((".jpg", ".jpeg"))
            else "image/png",
        )
        sdk = int(Build.VERSION.SDK_INT)
        if sdk >= 29:
            values.put(MediaColumns.RELATIVE_PATH, "Pictures/ColorSight")
            values.put(MediaColumns.IS_PENDING, 1)

        resolver = activity.getContentResolver()
        uri = resolver.insert(Images.EXTERNAL_CONTENT_URI, values)
        if uri is None:
            raise RuntimeError("MediaStore insert returned null")
        out = resolver.openOutputStream(uri)
        if out is None:
            raise RuntimeError("MediaStore openOutputStream failed")
        inp = FileInputStream(str(tmp))
        jbuf = autoclass("[B")(8192)
        try:
            while True:
                n = inp.read(jbuf)
                if n < 0:
                    break
                if n == 0:
                    continue
                out.write(jbuf, 0, n)
        finally:
            inp.close()
            out.close()

        if sdk >= 29:
            values.clear()
            values.put(MediaColumns.IS_PENDING, 0)
            resolver.update(uri, values, None, None)

        log.info("mediastore save ok album=Pictures/ColorSight")
        return "Saved to your gallery"
    except Exception as exc:
        _log_exc("mediastore save failed; using app files fallback", exc)
        dest = (
            Path(_android_activity().getExternalFilesDir(None).getAbsolutePath())
            / "ColorSight"
        )
        dest.mkdir(parents=True, exist_ok=True)
        encode_image(rgb, dest / filename, quality=95)
        return "Saved to your gallery"
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass
