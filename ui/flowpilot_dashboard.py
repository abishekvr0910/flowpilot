"""
FlowPilot native workspace shell with embedded Home, Studio and Settings.
Existing dictation, recovery and writing tools retain their production handlers.
"""

from typing import Optional, Callable, Dict, Any

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QPushButton, QButtonGroup, QMessageBox, QScrollArea
)
from PySide6.QtCore import Qt, Signal

from engine.companion_store import get_companion_store, CompanionStore
from engine.config import load_config, save_config
from ui.scratchpad_view import ScratchpadView
from ui.notetaker_view import NotetakerView
from ui.insights_view import InsightsView
from ui.transforms_view import TransformsView
from ui.history_view import HistoryView
from ui.dictionary_view import DictionaryView
from ui.snippets_view import SnippetsView
from ui.setup_wizard import SetupWizardDialog
from ui.settings_dialog import SettingsDialog
from ui.companion_studio import CompanionStudioDialog
from engine.text_injector import TextInjector
from engine.personalization import get_shared_personalization, PersonalizationEngine
from ui.workspace_style import workspace_style, harmonize_legacy_styles, label
from ui.workspace_home import WorkspaceHome


class FlowPilotDashboard(QMainWindow):
    dictate_requested = Signal()
    companion_changed = Signal(str)
    companion_settings_applied = Signal(dict)
    show_companion_requested = Signal()

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        on_save_config: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_dictate: Optional[Callable[[], None]] = None,
        personalization: Optional[PersonalizationEngine] = None,
        parent=None
    ):
        super().__init__(parent)
        self.config = config or load_config()
        self.on_save_config = on_save_config
        self.on_dictate = on_dictate
        self.personalization = personalization or get_shared_personalization()
        self.store: CompanionStore = get_companion_store()

        self.setWindowTitle("FlowPilot")
        self.resize(1160, 820)
        self.setMinimumSize(880, 580)

        self._init_styles()
        self._init_ui()
        self._apply_theme()

        # Center dashboard on primary screen
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.availableGeometry()
            x = geom.center().x() - (self.width() // 2)
            y = geom.center().y() - (self.height() // 2)
            self.move(x, y)

    def _init_styles(self):
        self.setStyleSheet(workspace_style(self.config.get("ui_theme", "sand")))

    def _apply_theme(self):
        theme = self.config.get("ui_theme", "sand")
        self.setStyleSheet(workspace_style(theme))
        self.stack.setStyleSheet("")
        for page in (self.transforms_view, self.dictionary_view, self.scratchpad_view,
                     self.notetaker_view, self.insights_view, self.snippets_view,
                     self.history_view):
            harmonize_legacy_styles(page, theme)
        for index in (8, 9):
            page = self.stack.widget(index)
            if isinstance(page, (CompanionStudioDialog, SettingsDialog)):
                page.setStyleSheet(workspace_style(theme))
                harmonize_legacy_styles(page, theme, include_root=False)

    def _init_ui(self):
        central = QWidget(self)
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Left Navigation Sidebar
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setMinimumWidth(180)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(14, 20, 14, 20)
        side_layout.setSpacing(6)

        side_layout.addWidget(label("flowpilot", "title"))
        side_layout.addWidget(label("Your voice. Your device.", "muted"))
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        groups = [
            ("WORKSPACE", [("Home", "home", 0), ("Scratchpad", "scratch", 3),
                           ("Meetings", "notes", 4)]),
            ("PERSONALIZE", [("Dictionary", "dict", 2), ("Snippets", "snippets", 6),
                             ("Companion Studio", "studio", 8)]),
            ("TOOLS", [("History and audio", "history", 7), ("Insights", "insights", 5),
                       ("Text edits", "transforms", 1)]),
        ]
        for heading, entries in groups:
            side_layout.addSpacing(14)
            side_layout.addWidget(label(heading, "eyebrow"))
            for title, attr, page in entries:
                button = self._create_nav_button(title, page)
                setattr(self, f"btn_nav_{attr}", button)
                side_layout.addWidget(button)
        side_layout.addStretch()
        self.btn_nav_settings = self._create_nav_button("Settings", 9)
        side_layout.addWidget(self.btn_nav_settings)
        side_layout.addWidget(label("Speech processing stays on device.", "muted"))

        self.sidebar_scroll = QScrollArea()
        self.sidebar_scroll.setWidgetResizable(True)
        self.sidebar_scroll.setFixedWidth(200)
        self.sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.sidebar_scroll.setWidget(sidebar)
        main_layout.addWidget(self.sidebar_scroll)

        # 2. Main Stacked Content Pages
        self.stack = QStackedWidget(self)
        self.stack.setStyleSheet("")

        # Page 0: Overview / Home
        page_home = self._build_home_page()
        self.stack.addWidget(page_home)

        # Page 1: Selected-Text Transforms
        self.transforms_view = TransformsView(self, on_dictate_toggle=self.on_dictate)
        self.stack.addWidget(self.transforms_view)

        # Page 2: Custom Dictionary & Glossary
        self.dictionary_view = DictionaryView(self, personalization=self.personalization)
        self.stack.addWidget(self.dictionary_view)

        # Page 3: Scratchpad
        self.scratchpad_view = ScratchpadView(self, on_dictate_toggle=self.on_dictate)
        self.stack.addWidget(self.scratchpad_view)

        # Page 4: Meeting Notetaker
        self.notetaker_view = NotetakerView(self)
        self.stack.addWidget(self.notetaker_view)

        # Page 5: Insights
        self.insights_view = InsightsView(self)
        self.stack.addWidget(self.insights_view)

        # Page 6: Voice Snippets
        self.snippets_view = SnippetsView(self, personalization=self.personalization)
        self.stack.addWidget(self.snippets_view)

        # Wire live synchronization so edits reflect immediately across all tabs
        self.personalization.add_change_listener(self.dictionary_view.reload_dictionary)
        self.personalization.add_change_listener(self.snippets_view.reload_snippets)

        # Page 7: Dictation History & Audio Replay
        self.history_view = HistoryView(self)
        self.stack.addWidget(self.history_view)

        # Pages 8/9 are constructed on demand with fresh saved settings.
        dummy_studio = QWidget()
        self.stack.addWidget(dummy_studio)

        dummy_settings = QWidget()
        self.stack.addWidget(dummy_settings)

        main_layout.addWidget(self.stack)

        self.btn_nav_home.setChecked(True)


    def _create_nav_button(self, text: str, index: int) -> QPushButton:
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setMinimumHeight(38)
        btn.setProperty("role", "nav")
        btn.setAccessibleName(text)
        btn.clicked.connect(lambda: self._on_nav_clicked(index))
        self.nav_group.addButton(btn, index)
        return btn

    def _on_nav_clicked(self, index: int):
        if index in (8, 9) and self.stack.currentIndex() != index:
            # Recreate from saved state on entry; drafts are never auto-applied.
            old_page = self.stack.widget(index)
            if index == 8:
                page = CompanionStudioDialog(self, embedded=True)
                page.applied.connect(self._on_companion_applied)
            else:
                page = SettingsDialog(self.config, self._on_save_settings,
                                      personalization=self.personalization, parent=self,
                                      embedded=True)
            page.rejected.connect(lambda: self._on_nav_clicked(0))
            self.stack.removeWidget(old_page)
            self.stack.insertWidget(index, page)
            old_page.deleteLater()
        self.stack.setCurrentIndex(index)
        button = self.nav_group.button(index)
        if button:
            button.setChecked(True)
        if index == 0:
            self.home_page.refresh()
        else:
            self.sidebar_scroll.setVisible(True)
            if index == 2:
                self.dictionary_view.reload_dictionary()
            elif index == 6:
                self.snippets_view.reload_snippets()
            elif index == 7:
                self.history_view.reload_history()
            elif index == 5:
                self.insights_view.refresh_metrics()

    def open_transforms(self, selected_text: Optional[str] = None):
        self.show()
        self.raise_()
        self.activateWindow()
        self.btn_nav_transforms.setChecked(True)
        self.stack.setCurrentIndex(1)
        if selected_text and hasattr(self, "transforms_view"):
            self.transforms_view.edit_original.setPlainText(selected_text)


    def _build_home_page(self) -> QWidget:
        self.home_page = WorkspaceHome(self)
        self.lbl_last_preview = self.home_page.last_preview
        return self.home_page

    def _run_setup_wizard(self):
        wizard = SetupWizardDialog(self, config=self.config)
        wizard.setup_completed.connect(self._on_save_settings)
        wizard.exec()

    def _on_quick_paste_last(self):
        target = TextInjector.last_target_hwnd
        if target:
            try:
                import win32gui
                if win32gui.IsWindow(target) and not TextInjector._is_flowpilot_window(target):
                    self.showMinimized()
                    from PySide6.QtCore import QTimer
                    QTimer.singleShot(150, lambda: self._do_paste_last(target))
                    return
            except Exception:
                pass
        self._do_paste_last(None)

    def _do_paste_last(self, target_hwnd: Optional[int] = None):
        res = TextInjector.inject_last(target_hwnd=target_hwnd)
        self.lbl_last_preview.setText(TextInjector.last_injected_text or "No text")
        if res.status.value in ("FAILED_RECOVERY_AVAILABLE", "ERROR") and not target_hwnd:
            QMessageBox.information(
                self,
                "Paste Recovery",
                "Last dictation text has been copied to your clipboard!\n\nSwitch to your intended application and press Ctrl+V to paste."
            )

    def _on_quick_copy_last(self):
        if TextInjector.last_injected_text:
            TextInjector._safe_clipboard_copy(TextInjector.last_injected_text)
            QMessageBox.information(self, "Copied", "Last dictation copied to clipboard!")
        else:
            QMessageBox.warning(self, "Empty", "No dictation text available to copy.")


    def _select_companion(self, asset_id: str):
        self.store.set("selected_asset_id", asset_id)
        self.companion_changed.emit(asset_id)
        self.home_page.refresh()

    def _on_companion_applied(self, new_data: dict):
        if new_data.get("action") == "show_live":
            self.show_companion_requested.emit()
            return
        asset_id = new_data.get("selected_asset_id", "kitty")
        self.companion_changed.emit(asset_id)
        self.companion_settings_applied.emit(dict(new_data))
        self.home_page.refresh()

    def _on_save_settings(self, new_config: dict):
        if self.on_save_config:
            if self.on_save_config(new_config) is False:
                return False
        self.config = dict(new_config)
        save_config(self.config)
        self._apply_theme()
        self.home_page.refresh()
        return True
