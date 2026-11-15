[app]
title = ColorSight
package.name = colorsight
package.domain = org.colorsight

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,ttf,otf,md,txt,xml
source.include_patterns = assets/*,assets/fonts/*,assets/icons/*,assets/android/*,docs/*,colorsight/*,core/*

version = 0.1.0

# Desktop deps stay in requirements.txt. Android: leave recipe deps unpinned for
# p4a 2026.05.09 / Python 3.14. Do NOT pin charset-normalizer here — p4a drops
# pins for pure-Python pip modules. CI uses constraints.txt + PIP_CONSTRAINT
# (charset-normalizer==3.4.9) so the dry-run resolver cannot pick 3.5.2's
# android_24_arm64_v8a wheel that host pip cannot install.
# camera4kivy needs gestures4kivy; CameraX Java comes from ./camerax_provider via p4a.hook
requirements = python3,kivy,numpy,opencv,pillow,pyjnius,android,camera4kivy,gestures4kivy

orientation = portrait
fullscreen = 0
# Camera4Kivy README historically capped api at 33 for camerax packages; 35 is fine
# with androidx CameraX 1.2.1 (vendored camerax_provider) on p4a 2026.05.09 / Py 3.14.
android.api = 35
android.minapi = 24
# p4a 2026.05.09 recommends NDK 28c; 25b fails NumPy 2.3 (libc++ unique.cpp).
android.ndk = 28c
android.accept_sdk_license = True

# CAMERA for live preview; READ_MEDIA_IMAGES for gallery fallback.
# No RECORD_AUDIO — we never record video/audio. camerax_provider may still add it
# in before_apk_build; assets/android/p4a_hook.py strips it from the final manifest.
# No broad WRITE on Android 10+ (MediaStore).
android.permissions = CAMERA,READ_MEDIA_IMAGES,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE

# 64-bit only — CameraX gradle deps are arch-specific; armeabi-v7a crashes on arm64 devices.
android.archs = arm64-v8a
android.allow_backup = True

# AndroidX (CameraX + FileProvider). CameraX deps also injected by camerax_provider hook.
android.enable_androidx = True
android.gradle_dependencies = androidx.core:core:1.12.0
android.add_resources = %(source.dir)s/assets/android/file_paths.xml:xml/file_paths.xml
# Best-effort FileProvider XML merge (many buildozer releases ignore this key):
android.extra_manifest_application_xml = %(source.dir)s/assets/android/fileprovider_snippet.xml
# Chains CameraX gradle_options (before) + FileProvider inject (after)
p4a.hook = %(source.dir)s/assets/android/p4a_hook.py

# Icons + splash (pastel eye / cream canvas)
icon.filename = %(source.dir)s/assets/icon.png
presplash.filename = %(source.dir)s/assets/presplash.png
android.presplash_color = #F6F4F1

# Adaptive icon layers (Android 8+)
android.icon.adaptive_foreground.filename = %(source.dir)s/assets/icon_foreground.png
android.icon.adaptive_background.filename = %(source.dir)s/assets/icon_background.png

[buildozer]
log_level = 2
warn_on_root = 1
