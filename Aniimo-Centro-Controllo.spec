# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [
    ('data/translation_it.csv', 'data'),
    ('data/supported_versions.json', 'data'),
    ('assets/aniimo-italian-installer-icon.ico', 'assets'),
]
binaries = []
hiddenimports = []
tmp_ret = collect_all('UnityPy')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['tools\\aniimo_it_gui.py'],
    pathex=['tools'],
    binaries=binaries,
    datas=datas,
    hiddenimports=['aniimo_it_installer'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pandas', 'openpyxl', 'lxml', 'matplotlib', 'scipy'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Aniimo-Centro-Controllo',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets\\aniimo-italian-installer-icon.ico',
)
