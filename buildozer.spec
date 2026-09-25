[app]
title = Lemus AI Music Studio
package.name = lemusaimusicstudio
package.domain = org.lemus.music
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 2.6.7

# КРИТИЧНО: python3 и hostpython3 одной версии, pyjnius явно
requirements = python3==3.11.9,hostpython3==3.11.9,kivy==2.3.0,kivymd==1.2.0,pillow,mutagen,pyjnius

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,RECORD_AUDIO,REQUEST_INSTALL_PACKAGES,POST_NOTIFICATIONS,MANAGE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a
android.allow_backup = True

# Принудительно чистим старые артефакты перед сборкой
android.clean_assets = True

[buildozer]
log_level = 2
warn_on_root = 1
