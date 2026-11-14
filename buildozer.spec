[app]
title = ColorSight
package.name = colorsight
package.domain = org.colorsight

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,ttf,otf,md,txt
source.include_patterns = assets/*,assets/fonts/*,assets/icons/*,docs/*,colorsight/*,core/*

version = 0.1.0

# Desktop deps listed in requirements.txt; Android recipes:
requirements = python3,kivy==2.3.0,numpy,opencv,pillow,pyjnius,android

orientation = portrait
fullscreen = 0
android.api = 33
android.minapi = 24
android.ndk = 25b
android.accept_sdk_license = True

android.permissions = CAMERA,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,READ_MEDIA_IMAGES

# FileProvider paths for share sheet (see assets/android/ + production.md)
android.add_maven_dependency = androidx.core:core:1.12.0
android.add_resources = %(source.dir)s/assets/android/file_paths.xml:xml/file_paths.xml

android.archs = arm64-v8a,armeabi-v7a
android.allow_backup = True

# Optional later:
# presplash.filename = %(source.dir)s/assets/presplash.png
# icon.filename = %(source.dir)s/assets/icon.png

[buildozer]
log_level = 2
warn_on_root = 1
