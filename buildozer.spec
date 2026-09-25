[app]
title = Lemus AI Music Studio
package.name = lemusaimusicstudio
package.domain = org.lemus.music
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 2.6.2

requirements = python3,kivy,kivymd,pillow,mutagen

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,RECORD_AUDIO,REQUEST_INSTALL_PACKAGES,POST_NOTIFICATIONS
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a
android.allow_backup = True

# Явно указываем Python 3.11 (стабильный, совместимый с Kivy)
p4a.python_version = 3.11

[buildozer]
log_level = 2
warn_on_root = 1
