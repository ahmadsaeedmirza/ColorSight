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
requirements = python3,kivy,numpy,opencv,pillow,pyjnius,android,camera4kivy

orientation = portrait
fullscreen = 0
android.api = 35
android.minapi = 24
# p4a 2026.05.09 recommends NDK 28c; 25b fails NumPy 2.3 (libc++ unique.cpp).
android.ndk = 28c
android.accept_sdk_license = True

# CAMERA for live preview; READ_MEDIA_IMAGES for gallery fallback.
# No broad WRITE on Android 10+ — MediaStore scoped storage is used instead.
# READ/WRITE_EXTERNAL_STORAGE kept for API < 29 devices only.
android.permissions = CAMERA,READ_MEDIA_IMAGES,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE

# 64-bit only — covers almost all current phones; skips armeabi-v7a build time.
android.archs = arm64-v8a
android.allow_backup = True

# FileProvider paths for share sheet
android.add_maven_dependency = androidx.core:core:1.12.0
android.add_resources = %(source.dir)s/assets/android/file_paths.xml:xml/file_paths.xml

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
