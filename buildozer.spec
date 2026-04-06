[app]
title = Fast Transfer
package.name = fasttransfer
package.domain = org.yourdomain

# Source files to include
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,html

# App Version
version = 1.0

# Requirements (These get baked into the APK)
requirements = python3,kivy,fastapi,uvicorn,aiofiles,python-multipart,typing-extensions,pydantic<2.0,starlette

# Android specific settings
android.permissions = INTERNET, ACCESS_WIFI_STATE, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True
android.accept_catch_all = True

[buildozer]
log_level = 2
warn_on_root = 1