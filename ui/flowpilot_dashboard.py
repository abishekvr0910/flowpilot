"""
FlowPilot Master Desktop Dashboard Window
Primary native Windows application providing:
- Left Navigation Rail (Overview, Dictation, Scratchpad, Notetaker, Insights, Companion Studio, Settings)
- Companion quick-switch bar (Kitty 🐾, Dog 🐶, Robot 🤖, Minimal Line 📏, Equalizer 🌊)
- Embedded Scratchpad Canvas & Meeting Notetaker
- Real-time productivity analytics
"""

import sys
import os
import getpass
from pathlib import Path
from typing import Optional, Callable, Dict, Any

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QPushButton, QLabel, QFrame, QButtonGroup, QMessageBox, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QFont

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


class FlowPilotDashboard(QMainWindow):
    dictate_requested = Signal()
    companion_changed = Signal(str)

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

        username = os.environ.get("USERNAME") or getpass.getuser() or "Abi"
        self.username = username.capitalize()

        self.setWindowTitle("FlowPilot - Voice Intelligence Dashboard")
        self.resize(1020, 680)
        self.setMinimumSize(880, 580)

        self._init_styles()
        self._init_ui()

        # Center dashboard on primary screen
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.availableGeometry()
            x = geom.center().x() - (self.width() // 2)
            y = geom.center().y() - (self.height() // 2)
            self.move(x, y)

    def _init_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0B0F19;
                color: #F8FAFC;
                font-family: 'Segoe UI', -apple-system, sans-serif;
            }
            QWidget#Sidebar {
                background-color: #0F172A;
                border-right: 1px solid #1E293B;
            }
            QLabel {
                color: #F8FAFC;
            }
        """)

    def _init_ui(self):
        central = QWidget(self)
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Left Navigation Sidebar
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(230)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(14, 20, 14, 20)
        side_layout.setSpacing(6)

        # Brand header
        brand_box = QHBoxLayout()
        lbl_logo = QLabel("|||| FlowPilot")
        lbl_logo.setStyleSheet("font-size: 19px; font-weight: bold; color: #38BDF8; letter-spacing: -0.5px;")
        brand_box.addWidget(lbl_logo)
        side_layout.addLayout(brand_box)

        lbl_badge = QLabel("100% Offline • Zero Egress")
        lbl_badge.setStyleSheet("font-size: 11px; color: #10B981; font-weight: 600; margin-bottom: 12px;")
        side_layout.addWidget(lbl_badge)

        # Navigation buttons
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        self.btn_nav_home = self._create_nav_button("🏠  Dashboard", 0)
        self.btn_nav_dict = self._create_nav_button("📖  Dictionary", 2)
        self.btn_nav_snippets = self._create_nav_button("⚡  Snippets", 6)
        self.btn_nav_scratch = self._create_nav_button("📝  Scratchpad", 3)
        self.btn_nav_notes = self._create_nav_button("🎙  Notetaker", 4)
        self.btn_nav_history = self._create_nav_button("📜  History & Audio", 7)
        self.btn_nav_insights = self._create_nav_button("📊  Insights", 5)
        self.btn_nav_transforms = self._create_nav_button("✨  Transforms", 1)
        self.btn_nav_studio = self._create_nav_button("🎨  Companion Studio", 8)
        self.btn_nav_settings = self._create_nav_button("⚙  Settings", 9)

        side_layout.addWidget(self.btn_nav_home)
        side_layout.addWidget(self.btn_nav_dict)
        side_layout.addWidget(self.btn_nav_snippets)
        side_layout.addWidget(self.btn_nav_scratch)
        side_layout.addWidget(self.btn_nav_notes)
        side_layout.addWidget(self.btn_nav_history)
        side_layout.addWidget(self.btn_nav_insights)
        side_layout.addWidget(self.btn_nav_transforms)
        side_layout.addWidget(self.btn_nav_studio)
        side_layout.addWidget(self.btn_nav_settings)

        side_layout.addStretch()

        # Bottom Freedom Callout
        promo = QFrame()
        promo.setStyleSheet("""
            QFrame {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        p_layout = QVBoxLayout(promo)
        p_layout.setContentsMargins(6, 6, 6, 6)
        p_layout.setSpacing(4)
        lbl_p1 = QLabel("Unlimited Words")
        lbl_p1.setStyleSheet("font-size: 12px; font-weight: bold; color: #38BDF8;")
        lbl_p2 = QLabel("No weekly limits or $15/mo paywalls.")
        lbl_p2.setStyleSheet("font-size: 11px; color: #94A3B8;")
        p_layout.addWidget(lbl_p1)
        p_layout.addWidget(lbl_p2)
        side_layout.addWidget(promo)

        main_layout.addWidget(sidebar)

        # 2. Main Stacked Content Pages
        self.stack = QStackedWidget(self)
        self.stack.setStyleSheet("background-color: #0B0F19;")

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

        # Page 8: Companion Studio Placeholder (Opens Dialog)
        dummy_studio = QWidget()
        self.stack.addWidget(dummy_studio)

        # Page 9: Settings Placeholder (Opens Dialog)
        dummy_settings = QWidget()
        self.stack.addWidget(dummy_settings)

        main_layout.addWidget(self.stack)

        self.btn_nav_home.setChecked(True)


    def _create_nav_button(self, text: str, index: int) -> QPushButton:
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 10px 14px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 600;
                color: #94A3B8;
                background-color: transparent;
                border: none;
            }
            QPushButton:hover {
                background-color: #1E293B;
                color: #F8FAFC;
            }
            QPushButton:checked {
                background-color: #1E293B;
                color: #38BDF8;
                border-left: 3px solid #38BDF8;
            }
        """)
        btn.clicked.connect(lambda: self._on_nav_clicked(index))
        self.nav_group.addButton(btn, index)
        return btn

    def _on_nav_clicked(self, index: int):
        if index == 8:
            # Open Companion Studio Modal
            studio = CompanionStudioDialog(self)
            studio.applied.connect(self._on_companion_applied)
            studio.exec()
            self.btn_nav_home.setChecked(True)
            self.stack.setCurrentIndex(0)
            return
        elif index == 9:
            # Open Settings Modal
            dlg = SettingsDialog(self.config, self._on_save_settings, parent=self)
            dlg.exec()
            self.btn_nav_home.setChecked(True)
            self.stack.setCurrentIndex(0)
            return

        self.stack.setCurrentIndex(index)
        if index == 2 and hasattr(self, "dictionary_view"):
            self.dictionary_view.reload_dictionary()
        elif index == 6 and hasattr(self, "snippets_view"):
            self.snippets_view.reload_snippets()
        elif index == 7 and hasattr(self, "history_view"):
            self.history_view.reload_history()
        elif index == 5 and hasattr(self, "insights_view"):
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
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        # Welcome Header
        top_bar = QHBoxLayout()
        title_box = QVBoxLayout()
        lbl_welcome = QLabel(f"Welcome back, {self.username}")
        lbl_welcome.setStyleSheet("font-size: 24px; font-weight: bold; color: #F8FAFC;")
        lbl_sub = QLabel("FlowPilot Desktop Voice Assistant • Ready to dictate across any application.")
        lbl_sub.setStyleSheet("font-size: 13px; color: #94A3B8;")
        title_box.addWidget(lbl_welcome)
        title_box.addWidget(lbl_sub)
        top_bar.addLayout(title_box)
        top_bar.addStretch()

        btn_dictate_now = QPushButton("🎤 Start Dictation (Ctrl+Shift+Space)")
        btn_dictate_now.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                color: white;
                font-weight: bold;
                font-size: 13px;
                padding: 10px 20px;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
        """)
        if self.on_dictate:
            btn_dictate_now.clicked.connect(self.on_dictate)
        top_bar.addWidget(btn_dictate_now)
        layout.addLayout(top_bar)

        # Status & Quick Answers Bar (Can I dictate now? What shortcut? What was last dictation?)
        status_bar = QHBoxLayout()
        status_bar.setSpacing(12)

        # Card 1: System Readiness
        card_readiness = QFrame()
        card_readiness.setStyleSheet("""
            QFrame {
                background-color: #0F172A;
                border: 1px solid #1E293B;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        cr_layout = QVBoxLayout(card_readiness)
        cr_layout.setSpacing(5)
        lbl_r_title = QLabel("● Ready to Dictate")
        lbl_r_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #10B981;")
        lbl_r_desc = QLabel("Faster-Whisper base (INT8 CPU)\n100% Offline • Zero Egress")
        lbl_r_desc.setStyleSheet("font-size: 11px; color: #94A3B8;")
        btn_wizard = QPushButton("🔧 Run Setup Wizard")
        btn_wizard.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #38BDF8;
                border: 1px solid #334155;
                font-size: 11px;
                font-weight: 600;
                padding: 5px 10px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #334155; }
        """)
        btn_wizard.clicked.connect(self._run_setup_wizard)
        cr_layout.addWidget(lbl_r_title)
        cr_layout.addWidget(lbl_r_desc)
        cr_layout.addWidget(btn_wizard)
        status_bar.addWidget(card_readiness, 1)

        # Card 2: Active Controls
        card_ctrl = QFrame()
        card_ctrl.setStyleSheet("""
            QFrame {
                background-color: #0F172A;
                border: 1px solid #1E293B;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        cc_layout = QVBoxLayout(card_ctrl)
        cc_layout.setSpacing(5)
        lbl_c_title = QLabel("⌨ Active Controls")
        lbl_c_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #38BDF8;")
        hk = self.config.get("hotkey", "Ctrl+Shift+Space")
        lang = str(self.config.get("language", "auto")).upper()
        lbl_c_desc = QLabel(f"Dictation Hotkey: {hk}\nLanguage: {lang}\nRecovery: Shift+Alt+Z")
        lbl_c_desc.setStyleSheet("font-size: 11px; color: #94A3B8;")
        cc_layout.addWidget(lbl_c_title)
        cc_layout.addWidget(lbl_c_desc)
        status_bar.addWidget(card_ctrl, 1)

        # Card 3: Last Dictation & Fast Recovery
        card_rec = QFrame()
        card_rec.setStyleSheet("""
            QFrame {
                background-color: #0F172A;
                border: 1px solid #1E293B;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        crec_layout = QVBoxLayout(card_rec)
        crec_layout.setSpacing(5)
        lbl_rec_title = QLabel("📋 Last Dictation & Recovery")
        lbl_rec_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #F8FAFC;")
        self.lbl_last_preview = QLabel(TextInjector.last_injected_text or "No dictations yet in this session.")
        self.lbl_last_preview.setStyleSheet("font-size: 11px; color: #94A3B8; font-style: italic;")
        self.lbl_last_preview.setWordWrap(True)

        rec_btn_box = QHBoxLayout()
        rec_btn_box.setSpacing(6)
        btn_paste_last = QPushButton("📋 Paste Last (Shift+Alt+Z)")
        btn_paste_last.setStyleSheet("background-color: #1E293B; color: #CBD5E1; border: 1px solid #334155; font-size: 11px; padding: 4px 8px; border-radius: 4px; font-weight: 600;")
        btn_paste_last.clicked.connect(self._on_quick_paste_last)

        btn_copy_last = QPushButton("📄 Copy Last (Shift+Alt+X)")
        btn_copy_last.setStyleSheet("background-color: #1E293B; color: #CBD5E1; border: 1px solid #334155; font-size: 11px; padding: 4px 8px; border-radius: 4px; font-weight: 600;")
        btn_copy_last.clicked.connect(self._on_quick_copy_last)

        rec_btn_box.addWidget(btn_paste_last)
        rec_btn_box.addWidget(btn_copy_last)

        crec_layout.addWidget(lbl_rec_title)
        crec_layout.addWidget(self.lbl_last_preview)
        crec_layout.addLayout(rec_btn_box)
        status_bar.addWidget(card_rec, 2)

        layout.addLayout(status_bar)

        # Active Companion Quick Switcher Card
        card_pet = QFrame()
        card_pet.setStyleSheet("""
            QFrame {
                background-color: #0F172A;
                border: 1px solid #1E293B;
                border-radius: 10px;
                padding: 16px;
            }
        """)
        cp_layout = QVBoxLayout(card_pet)
        cp_layout.setSpacing(10)

        lbl_cp_title = QLabel("Desktop Companion Selection")
        lbl_cp_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #F8FAFC;")
        lbl_cp_desc = QLabel("Choose your interactive floating companion on your screen:")
        lbl_cp_desc.setStyleSheet("font-size: 12px; color: #94A3B8;")
        cp_layout.addWidget(lbl_cp_title)
        cp_layout.addWidget(lbl_cp_desc)

        pet_btn_layout = QHBoxLayout()
        pet_btn_layout.setSpacing(8)

        current_pet = self.store.get("selected_asset_id", "dog")

        pets_row1 = [
            ("dog", "🐶 Pixel Pup"),
            ("kitty", "🐾 Pixel Kitty"),
            ("fox", "🦊 Pixel Fox"),
            ("dino", "🦖 Pixel Dino"),
            ("ghost", "👻 Pixel Ghost"),
            ("bunny", "🐰 Pixel Bunny"),
        ]

        pets_row2 = [
            ("mascot", "🤖 Pilot Robot"),
            ("wave_bar", "🌊 Sound Waves"),
            ("edge_line", "📏 Docked Line"),
        ]

        self.pet_buttons: Dict[str, QPushButton] = {}
        for pet_id, label in pets_row1:
            pbtn = QPushButton(label)
            is_active = (pet_id == current_pet)
            pbtn.setStyleSheet(self._pet_btn_style(is_active))
            pbtn.clicked.connect(lambda _, pid=pet_id: self._select_companion(pid))
            self.pet_buttons[pet_id] = pbtn
            pet_btn_layout.addWidget(pbtn)

        cp_layout.addLayout(pet_btn_layout)

        pet_btn_layout2 = QHBoxLayout()
        pet_btn_layout2.setSpacing(8)
        for pet_id, label in pets_row2:
            pbtn = QPushButton(label)
            is_active = (pet_id == current_pet)
            pbtn.setStyleSheet(self._pet_btn_style(is_active))
            pbtn.clicked.connect(lambda _, pid=pet_id: self._select_companion(pid))
            self.pet_buttons[pet_id] = pbtn
            pet_btn_layout2.addWidget(pbtn)

        pet_btn_layout2.addStretch()
        cp_layout.addLayout(pet_btn_layout2)

        btn_open_studio = QPushButton("🎨 Customize Appearance, Fur & Motion in Companion Studio →")
        btn_open_studio.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #38BDF8;
                font-weight: 600;
                font-size: 12px;
                padding: 8px 14px;
                border-radius: 6px;
                border: 1px solid #334155;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #334155;
            }
        """)
        btn_open_studio.clicked.connect(lambda: self._on_nav_clicked(8))
        cp_layout.addWidget(btn_open_studio)

        layout.addWidget(card_pet)

        # Quick Actions Grid
        quick_grid = QHBoxLayout()
        quick_grid.setSpacing(12)

        q_dict = self._make_quick_card(
            "📖 Custom Dictionary",
            "Teach local engine custom words, code identifiers, and proper names.",
            "Open Dictionary →",
            lambda: self._on_nav_clicked(2)
        )
        quick_grid.addWidget(q_dict)

        q_snip = self._make_quick_card(
            "⚡ Voice Snippets",
            "Expand short spoken trigger phrases into full templates and links.",
            "Open Snippets →",
            lambda: self._on_nav_clicked(6)
        )
        quick_grid.addWidget(q_snip)

        q1 = self._make_quick_card(
            "📝 Voice Scratchpad",
            "Open your dedicated drafting canvas with real-time word counting, bullet formatting, and export.",
            "Open Scratchpad →",
            lambda: self._on_nav_clicked(3)
        )
        quick_grid.addWidget(q1)

        q2 = self._make_quick_card(
            "🎙 Meeting Notetaker",
            "Record meetings, generate timestamped rolling transcripts, and extract action items 100% offline.",
            "Open Notetaker →",
            lambda: self._on_nav_clicked(4)
        )
        quick_grid.addWidget(q2)

        q3 = self._make_quick_card(
            "📊 Productivity Insights",
            "Inspect your lifetime words, dictation WPM velocity, active streaks, and hours saved vs. typing.",
            "View Analytics →",
            lambda: self._on_nav_clicked(5)
        )
        quick_grid.addWidget(q3)

        layout.addLayout(quick_grid)
        layout.addStretch()

        return widget

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

    def _pet_btn_style(self, active: bool) -> str:
        if active:
            return """
                QPushButton {
                    background-color: #0284C7;
                    color: #FFFFFF;
                    font-weight: bold;
                    padding: 9px 14px;
                    border-radius: 6px;
                    border: 1px solid #38BDF8;
                    font-size: 13px;
                }
            """
        return """
            QPushButton {
                background-color: #1E293B;
                color: #94A3B8;
                font-weight: 600;
                padding: 9px 14px;
                border-radius: 6px;
                border: 1px solid #334155;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #F8FAFC;
            }
        """

    def _select_companion(self, asset_id: str):
        self.store.set("selected_asset_id", asset_id)
        for pid, btn in self.pet_buttons.items():
            btn.setStyleSheet(self._pet_btn_style(pid == asset_id))
        self.companion_changed.emit(asset_id)

    def _on_companion_applied(self, new_data: dict):
        asset_id = new_data.get("selected_asset_id", "kitty")
        for pid, btn in self.pet_buttons.items():
            btn.setStyleSheet(self._pet_btn_style(pid == asset_id))
        self.companion_changed.emit(asset_id)

    def _on_save_settings(self, new_config: dict):
        self.config = dict(new_config)
        save_config(self.config)
        if self.on_save_config:
            self.on_save_config(new_config)

    def _make_quick_card(self, title: str, desc: str, btn_text: str, on_click: Callable[[], None]) -> QFrame:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #0F172A;
                border: 1px solid #1E293B;
                border-radius: 10px;
                padding: 16px;
            }
        """)
        vbox = QVBoxLayout(card)
        vbox.setSpacing(8)

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("font-size: 15px; font-weight: bold; color: #F8FAFC;")
        vbox.addWidget(lbl_t)

        lbl_d = QLabel(desc)
        lbl_d.setWordWrap(True)
        lbl_d.setStyleSheet("font-size: 12px; color: #94A3B8; line-height: 1.4;")
        vbox.addWidget(lbl_d)

        vbox.addStretch()

        btn = QPushButton(btn_text)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #38BDF8;
                font-weight: 600;
                font-size: 12px;
                padding: 7px 12px;
                border-radius: 6px;
                border: 1px solid #334155;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #334155;
            }
        """)
        btn.clicked.connect(on_click)
        vbox.addWidget(btn)

        return card
