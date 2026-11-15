"""p4a hook: inject FileProvider into AndroidManifest before Gradle packages the APK.

``after_apk_build`` runs after the dist project is prepared and before the final
APK assemble — despite the name. Official buildozer still lacks a reliable
``android.extra_manifest_application_xml`` / content-providers option, so this
hook is the supported workaround.
"""

from __future__ import annotations

from pathlib import Path

_PROVIDER = """
        <provider
            android:name="androidx.core.content.FileProvider"
            android:authorities="{package}.fileprovider"
            android:exported="false"
            android:grantUriPermissions="true">
            <meta-data
                android:name="android.support.FILE_PROVIDER_PATHS"
                android:resource="@xml/file_paths" />
        </provider>
"""


def after_apk_build(toolchain) -> None:
    dist = Path(toolchain._dist.dist_dir)
    manifest = dist / "src" / "main" / "AndroidManifest.xml"
    if not manifest.is_file():
        print(f"[ColorSight FileProvider] ERROR: missing {manifest}")
        return

    text = manifest.read_text(encoding="utf-8")
    if "androidx.core.content.FileProvider" in text or ".fileprovider" in text:
        print("[ColorSight FileProvider] provider already present — OK")
        _ensure_file_paths(dist)
        return

    package = getattr(getattr(toolchain, "_dist", None), "package_name", None)
    if not package:
        # Fallback: parse package= from manifest root
        package = "org.colorsight.colorsight"
        for token in text.split():
            if token.startswith('package="') and token.endswith('"'):
                package = token[len('package="') : -1]
                break

    snippet = _PROVIDER.format(package=package)
    if "</application>" not in text:
        print("[ColorSight FileProvider] ERROR: no </application> in manifest")
        return

    new_text = text.replace("</application>", snippet + "\n    </application>", 1)
    manifest.write_text(new_text, encoding="utf-8")
    print(f"[ColorSight FileProvider] injected authority={package}.fileprovider")
    _ensure_file_paths(dist)


def _ensure_file_paths(dist: Path) -> None:
    """Copy file_paths.xml into res/xml if android.add_resources did not."""
    dest_dir = dist / "src" / "main" / "res" / "xml"
    dest = dest_dir / "file_paths.xml"
    if dest.is_file():
        print("[ColorSight FileProvider] @xml/file_paths already present — OK")
        return

    # Hook lives at assets/android/p4a_fileprovider_hook.py; sibling is file_paths.xml
    src = Path(__file__).resolve().parent / "file_paths.xml"
    if not src.is_file():
        print(f"[ColorSight FileProvider] WARNING: missing source {src}")
        return
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"[ColorSight FileProvider] wrote {dest}")
