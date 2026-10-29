# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

block_cipher = None

# Never allow a future copied competitor renderer or credential bridge into a
# frozen build, even if an ignored local file reappears under ui/.
for forbidden in ('ui/wispr_renderer', 'ui/wispr_bridge.py', 'ui/assets'):
    if Path(forbidden).exists():
        raise RuntimeError(f'Forbidden third-party UI material in build input: {forbidden}')

added_files = [
    # Python modules are bundled by Analysis/PYZ. Only the integration server's
    # own static files belong in the on-disk ui/ data directory; copying the
    # whole source tree would also ship stale __pycache__ files.
    ('ui/index.html', 'ui'),
    ('ui/app.js', 'ui'),
    ('ui/styles.css', 'ui'),
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
    'PIL',
    'PIL.Image',
    'PIL.ImageSequence',
    'engine.silero_vad',
    'engine.single_instance',
    'engine.companion_store',
    'engine.companion_visibility',
    'engine.media_presence',
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
    'engine.local_text_repair',
    'engine.writing_intelligence',
    'engine.correction_intent',
    'engine.stt_engine',
    'engine.context_processor',
    'engine.audio_recorder',
    'engine.hotkey_service',
    'engine.orchestrator',
    'engine.session',
    'engine.config',
    'engine.text_injector',
    'engine.personalization',
    'engine.language_registry',
    'engine.selection_rewriter',
    'ui.companion_studio',
    'ui.companion_visibility_controller',
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
    'ui.workspace_home',
    'ui.workspace_style',
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
    # These optional stacks are not imported by FlowPilot. Keeping them out of
    # the frozen app removes hundreds of MB pulled in by broad dependency hooks.
    excludes=[
        'tkinter', 'matplotlib', 'scipy.spatial.cKDTree',
        'pyarrow', 'pandas', 'boto3', 'botocore', 'lxml',
        'psycopg', 'psycopg2', 'sqlalchemy',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# FlowPilot does not import these optional Qt modules. PyInstaller's broad Qt
# hook otherwise bundles their plugins and native libraries with every build.
# Qt Virtual Keyboard has a different open source license boundary, and Qt PDF
# pulls in PDFium notices; neither is needed by this widgets based desktop app.
unused_qt_files = {
    'qt6virtualkeyboard.dll', 'qtvirtualkeyboardplugin.dll',
    'qt6pdf.dll', 'qpdf.dll',
}
a.binaries = [entry for entry in a.binaries
              if Path(entry[0]).name.lower() not in unused_qt_files]
a.datas = [entry for entry in a.datas
           if Path(entry[0]).name.lower() not in unused_qt_files]

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
