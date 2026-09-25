[app]
title = Lemus AI Music Studio
package.name = lemusaimusicstudio
package.domain = org.lemus.music
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 2.6.2

# ВАЖНО: явные версии! python3 БЕЗ версии тянет нестабильный 3.13
requirements = python3==3.11.4,kivy==2.3.0,kivymd==1.2.0,pillow==10.1.0,mutagen==1.47.0

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,READ_MEDIA_AUDIO,RECORD_AUDIO,REQUEST_INSTALL_PACKAGES,INSTALL_PACKAGES,VIBRATE,POST_NOTIFICATIONS
android.api = 33
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a
android.allow_backup = True

# Явно отключаем экспериментальный JIT в Python 3.13+ (страховка)
p4a.python_version = 3.11

[buildozer]
log_level = 2
warn_on_root = 1
