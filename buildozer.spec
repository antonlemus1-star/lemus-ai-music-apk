[app]
title = Lemus AI Music Studio
package.name = lemusaimusicstudio
package.domain = org.lemus.music
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 2.6.6

# Явные стабильные версии + pyjnius для Android-интеграции
requirements = python3==3.10.14,kivy==2.3.0,kivymd==1.2.0,pillow,mutagen,pyjnius

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,READ_MEDIA_AUDIO,RECORD_AUDIO,REQUEST_INSTALL_PACKAGES,INSTALL_PACKAGES,VIBRATE,POST_NOTIFICATIONS,MANAGE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
