# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules("mitmproxy") + ["miutils"]

a = Analysis(
    ["mac_app.py"],
    pathex=[".", "vendor"],
    binaries=[],
    datas=[("app.py", ".")],
    hiddenimports=hiddenimports,
    hookspath=["vendor/mitmproxy/utils/pyinstaller"],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Xiaomi Mitmproxy",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch="arm64",
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Xiaomi Mitmproxy",
)

app = BUNDLE(
    coll,
    name="Xiaomi Mitmproxy.app",
    icon=None,
    bundle_identifier="com.xiaomi-mitmproxy.app",
)
