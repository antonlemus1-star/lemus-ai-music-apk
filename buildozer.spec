[app]
title = Lemus AI Music Studio
package.name = lemusaimusicstudio
package.domain = org.lemus.music
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 2.6.3

# Проверенный комплект: Python 3.11 + Kivy 2.3.0 + KivyMD 1.2.0
requirements = python3==3.11.9,kivy==2.3.0,kivymd==1.2.0,pillow,mutagen

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,RECORD_AUDIO,REQUEST_INSTALL_PACKAGES,POST_NOTIFICATIONS
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a
android.allow_backup = True

# Стабильная ветка python-for-android вместо master-2026
p4a.branch = release-2024.01.21

[buildozer]
log_level = 2
warn_on_root = 1
