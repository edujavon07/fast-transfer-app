[app]
# (str) Title of your application
title = Fast Transfer

# (str) Package name
package.name = fasttransfer

# (str) Package domain (needed for android/ios packaging)
package.domain = org.yourdomain

# (str) Source code where the main.py lives
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,html

# (str) Application versioning
version = 1.0

# (list) Application requirements
# Added h11, click, anyio, sniffio, and idna to guarantee NO hidden Uvicorn/FastAPI import crashes!
requirements = python3,kivy,fastapi,uvicorn,aiofiles,python-multipart,typing-extensions,pydantic<2.0,starlette,h11,click,anyio,sniffio,idna

# (list) Permissions
android.permissions = INTERNET, ACCESS_WIFI_STATE, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE

# (int) Target Android API, should be as high as possible.
android.api = 33

# (int) Minimum API your APK / AAB will support.
android.minapi = 21

# (str) Android architecture to build for (only arm64-v8a to prevent memory crashes)
android.archs = arm64-v8a

# (bool) enables Android auto backup feature (Android API >=23)
android.allow_backup = True

# (bool) If True, then skip trying to update the Android sdk
android.accept_catch_all = True

[buildozer]
# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1
