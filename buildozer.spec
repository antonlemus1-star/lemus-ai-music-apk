[app]
title = Lemus AI Music Studio
package.name = lemusaimusicstudio
package.domain = org.lemus.music
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 3.0.0

# Явные версии: python3 и hostpython3 ОБЯЗАТЕЛЬНО совпадают
requirements = python3==3.11.9,hostpython3==3.11.9,kivy==2.3.0,kivymd==1.2.0,mutagen,pyjnius

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,RECORD_AUDIO,REQUEST_INSTALL_PACKAGES,POST_NOTIFICATIONS,MANAGE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a
android.allow_backup = True
android.accept_sdk_license = True

# НЕ указываем p4a.branch — используем master (поддерживает 3.11.9)

[buildozer]
log_level = 2
warn_on_root = 1
