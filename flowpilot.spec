# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

block_cipher = None

added_files = [
    ('engine', 'engine'),
    ('ui', 'ui'),
    ('assets', 'assets'),
    ('assets', 'faster_whisper/assets'),
]
if os.path.isdir('models'):
    added_files.append(('models', 'models'))
added_files += collect_data_files('faster_whisper')
added_files += collect_data_files('onnxruntime')

added_binaries = []
added_binaries += collect_dynamic_libs('onnxruntime')
added_binaries += collect_dynamic_libs('ctranslate2')

hidden_imports = [
    'faster_whisper',
    'onnxruntime',
    'onnxruntime.capi._pybind_state',
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
    'engine.silero_vad',
    'engine.single_instance',
    'engine.companion_store',
    'engine.companion_assets',
    'engine.preference_learning',
    'engine.insights_engine',
    'engine.meeting_notetaker',
    'engine.meeting_deliberation',
    'engine.voice_editor',
    'engine.evaluation_metrics',
    'engine.prompt_budget',
    'engine.real_voice_corpus',
    'engine.transforms_engine',
    'engine.history_vault',
    'engine.local_llm',
    'engine.writing_intelligence',
    'engine.stt_engine',
    'engine.context_processor',
    'engine.audio_capture',
    'engine.hotkey_listener',
    'engine.orchestrator',
    'engine.session',
    'engine.config',
    'engine.text_injector',
    'engine.personalization',
    'engine.language_registry',
    'ui.companion_studio',
    'ui.companion_renderer',
    'ui.companion_preview',
    'ui.pixel_creator',
    'ui.pet_sprites',
    'ui.scratchpad_view',
    'ui.notetaker_view',
    'ui.insights_view',
    'ui.transforms_view',
    'ui.dictionary_view',
    'ui.snippets_view',
    'ui.setup_wizard',
    'ui.history_view',
    'ui.flowpilot_dashboard',
    'ui.floating_hud',
    'ui.tray_manager',
    'ui.settings_dialog',
    'PySide6.QtCore',
    'PySide6.QtWidgets',
    'PySide6.QtGui',
]

a = Analysis(
    ['desktop_app.py'],
    pathex=['.'],
    binaries=added_binaries,
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
