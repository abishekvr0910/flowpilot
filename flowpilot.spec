# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from pathlib import Path

block_cipher = None

added_files = [
    ('engine', 'engine'),
    ('ui', 'ui'),
]

hidden_imports = [
    'faster_whisper',
    'sounddevice',
    'soundfile',
    'cffi',
    'pycaw',
    'comtypes',
    'comtypes.client',
    'pyperclip',
    'win32gui',
    'win32con',
    'win32process',
    'win32api',
    'pynput',
    'pynput.keyboard',
    'PySide6.QtCore',
    'PySide6.QtWidgets',
    'PySide6.QtGui',
]

a = Analysis(
    ['desktop_app.py'],
    pathex=['.'],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy.spatial.cKDTree'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FlowPilot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # Desktop GUI mode without background terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='FlowPilot',
)
