[app]
title = Texas Hold'em Poker
package.name = texasholdem
package.domain = org.tencent.poker

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf

version = 1.0.0

requirements = python3,kivy==2.3.0,kivymd

orientation = landscape

fullscreen = 1

android.permissions = INTERNET

android.api = 33
android.minapi = 21
android.ndk = 25b
android.sdk = 33
android.ndk_api = 21
android.archs = arm64-v8a, armeabi-v7a

android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
