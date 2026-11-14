[app]
title = ColorSight
package.name = colorsight
package.domain = org.colorsight

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,ttf,otf,md,txt,xml
source.include_patterns = assets/*,assets/fonts/*,assets/icons/*,assets/android/*,docs/*,colorsight/*,core/*

version = 0.1.0
version.regex = __version__ = ['"](.*)['"]
version.filename = %(source.dir)s/colorsight/__init__.py

# Desktop deps in requirements.txt; Android recipes (pinned where recipes allow):
requirements = python3,kivy==2.3.0,numpy==1.26.4,opencv,pillow==10.4.0,pyjnius,android,camera4kivy

orientation = portrait
fullscreen = 0
android.api = 33
android.minapi = 24
android.ndk = 25b
android.accept_sdk_license = True

# CAMERA for live preview; READ_MEDIA_IMAGES for gallery fallback.
# No broad WRITE on Android 10+ — MediaStore scoped storage is used instead.
# READ/WRITE_EXTERNAL_STORAGE kept for API < 29 devices only.
android.permissions = CAMERA,READ_MEDIA_IMAGES,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE

android.archs = arm64-v8a,armeabi-v7a
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
