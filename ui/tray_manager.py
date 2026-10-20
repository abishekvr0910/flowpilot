"""
FlowPilot System Tray Manager
Handles background presence, system tray notifications, and tray context menu.
"""

from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen
from PySide6.QtCore import Qt, Signal, QObject

class TrayManager(QObject):
    toggle_requested = Signal()
    cancel_requested = Signal()
    recopy_requested = Signal()
    reinject_requested = Signal()
    dashboard_requested = Signal()
    toggle_hud_requested = Signal()
    restore_hud_requested = Signal()
    switch_visual_requested = Signal()
    settings_requested = Signal()
    studio_requested = Signal()
    quit_requested = Signal()
    ducking_toggled = Signal(bool)
    language_changed = Signal(str)
    translate_toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tray_icon = QSystemTrayIcon(parent)
        self._init_icons()
        self._init_menu()
        self.set_state("idle")
        self.tray_icon.show()

    def _create_icon_pixmap(self, bg_color: str, symbol: str) -> QIcon:
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw circular background
        painter.setBrush(QBrush(QColor(bg_color)))
        painter.setPen(QPen(QColor(255, 255, 255, 180), 1.5))
        painter.drawEllipse(2, 2, 28, 28)

        # Draw symbol/text
        painter.setPen(QColor("#FFFFFF"))
        font = painter.font()
        font.setPixelSize(14)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignCenter, symbol)
        painter.end()

        return QIcon(pixmap)

    def _init_icons(self):
        self.icon_idle = self._create_icon_pixmap("#0284C7", "FP")
        self.icon_recording = self._create_icon_pixmap("#DC2626", "REC")
        self.icon_processing = self._create_icon_pixmap("#D97706", "STT")

    def _init_menu(self):
        self.menu = QMenu()
        self.menu.setStyleSheet("""
            QMenu {
                background-color: #0F172A;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #0284C7;
                color: #FFFFFF;
            }
        """)

        self.action_dash = self.menu.addAction("🚀 Open FlowPilot Dashboard")
        self.action_dash.triggered.connect(self.dashboard_requested.emit)

        self.menu.addSeparator()

        self.action_toggle = self.menu.addAction("Dictate (Ctrl+Shift+Space)")
        self.action_toggle.triggered.connect(self.toggle_requested.emit)

        self.action_hud = self.menu.addAction("Show/Hide Desktop Companion")
        self.action_hud.triggered.connect(self.toggle_hud_requested.emit)

        self.action_restore = self.menu.addAction("Restore Companion to Bottom-Right")
        self.action_restore.triggered.connect(self.restore_hud_requested.emit)

        self.action_studio = self.menu.addAction("🎨 Companion Studio...")
        self.action_studio.triggered.connect(self.studio_requested.emit)

        self.action_switch_visual = self.menu.addAction("Cycle Appearance Style...")
        self.action_switch_visual.triggered.connect(self.switch_visual_requested.emit)

        self.menu.addSeparator()

        self.action_duck = self.menu.addAction("Silence Background Audio")
        self.action_duck.setCheckable(True)
        self.action_duck.setChecked(True)
        self.action_duck.toggled.connect(self.ducking_toggled.emit)

        self.action_reinject = self.menu.addAction("📋 Paste Last Dictation (Shift+Alt+Z)")
        self.action_reinject.triggered.connect(self.reinject_requested.emit)

        self.action_recopy = self.menu.addAction("📄 Copy Last Dictation (Shift+Alt+X)")
        self.action_recopy.triggered.connect(self.recopy_requested.emit)

        # Language & Live Translation Submenu
        self.lang_menu = self.menu.addMenu("🌐 Language & Translation")
        self.lang_actions = {}
        top_languages = [
            ("auto", "Auto-Detect (99 Languages)"),
            ("en", "English"),
            ("es", "Spanish (Español)"),
            ("fr", "French (Français)"),
            ("de", "German (Deutsch)"),
            ("it", "Italian (Italiano)"),
            ("pt", "Portuguese (Português)"),
            ("ru", "Russian (Русский)"),
            ("zh", "Chinese (中文)"),
            ("ja", "Japanese (日本語)"),
            ("ar", "Arabic (العربية)"),
            ("hi", "Hindi (हिन्दी)")
        ]
        from PySide6.QtGui import QActionGroup
        self.lang_group = QActionGroup(self)
        self.lang_group.setExclusive(True)
        for code, name in top_languages:
            act = self.lang_menu.addAction(name)
            act.setCheckable(True)
            self.lang_group.addAction(act)
            self.lang_actions[code] = act
            act.triggered.connect(lambda checked=False, c=code: self.language_changed.emit(c))

        self.lang_menu.addSeparator()
        self.action_translate = self.lang_menu.addAction("🌐 Translate Speech to English")
        self.action_translate.setCheckable(True)
        self.action_translate.toggled.connect(self.translate_toggled.emit)

        act_more_lang = self.lang_menu.addAction("More Languages... (Settings)")
        act_more_lang.triggered.connect(self.settings_requested.emit)

        self.action_settings = self.menu.addAction("Settings & History...")
        self.action_settings.triggered.connect(self.settings_requested.emit)

        self.menu.addSeparator()

        self.action_quit = self.menu.addAction("Exit FlowPilot")
        self.action_quit.triggered.connect(self.quit_requested.emit)

        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.activated.connect(self._on_tray_activated)

    def set_language_info(self, current_lang: str, is_translate: bool = False):
        cur = (current_lang or "auto").lower()
        if cur in self.lang_actions:
            self.lang_actions[cur].setChecked(True)
        if hasattr(self, 'action_translate'):
            self.action_translate.setChecked(is_translate)

    def set_hotkey_info(self, hotkey_str: str, mode: str = "toggle"):
        clean_hk = hotkey_str.replace("<", "").replace(">", "").strip()
        self._hotkey_str = clean_hk
        self._mode = mode
        if hasattr(self, 'action_toggle'):
            if mode == "push_to_talk":
                self.action_toggle.setText(f"Dictate (Hold {clean_hk})")
            else:
                self.action_toggle.setText(f"Dictate ({clean_hk})")

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            # Single click toggles dictation
            self.toggle_requested.emit()
        elif reason == QSystemTrayIcon.DoubleClick:
            self.dashboard_requested.emit()

    def set_state(self, state: str):
        st = state.lower()
        hk = getattr(self, '_hotkey_str', 'Ctrl+Shift+Space')
        if st in ("listening", "recording"):
            self.tray_icon.setIcon(self.icon_recording)
            self.tray_icon.setToolTip("FlowPilot: Listening... (Recording Voice)")
            self.action_toggle.setText(f"Stop & Paste ({hk})")
        elif st in ("starting", "starting_recording"):
            self.tray_icon.setIcon(self.icon_processing)
            self.tray_icon.setToolTip("FlowPilot: Starting microphone...")
            self.action_toggle.setText("Starting mic...")
        elif st in ("processing", "transcribing", "formatting", "inserting_text"):
            self.tray_icon.setIcon(self.icon_processing)
            self.tray_icon.setToolTip("FlowPilot: Transcribing speech...")
            self.action_toggle.setText("Processing...")
        elif st in ("unverified", "sent_unverified"):
            self.tray_icon.setIcon(self.icon_processing)
            self.tray_icon.setToolTip("FlowPilot: Sent — unverified target (please check)")
            self.action_toggle.setText("Unverified target (check)")
        else:
            self.tray_icon.setIcon(self.icon_idle)
            self.tray_icon.setToolTip(f"FlowPilot: Ready ({hk})")
            self.action_toggle.setText(f"Start Dictation ({hk})")

    def show_notification(self, title: str, message: str, is_error: bool = False, is_warning: bool = False):
        if is_error:
            icon = QSystemTrayIcon.Critical
        elif is_warning:
            icon = QSystemTrayIcon.Warning
        else:
            icon = QSystemTrayIcon.Information
        self.tray_icon.showMessage(title, message, icon, 4000)
