"""
Feature 19: FlowPilot Companion Studio
Interactive native configuration window for desktop companions:
- Explicit character selection (Kitty, Robot, Docked Line, Equalizer, and Custom Creations).
- Appearance locking to eliminate accidental double-click cycling.
- Custom emoji, transparent PNG, and sprite pack creation with safe export/import.
- Motion presets (breathe, gentle bob, tiny tilt, audio pulse, celebration, reduced motion).
- Hermes-inspired local preference learning review, rule management, and explicit vocabulary teaching.
"""

import sys
import os
import logging

logger = logging.getLogger("FlowPilot.CompanionStudio")
from pathlib import Path
from typing import Dict, Any, Optional

from PySide6.QtWidgets import (
    QDialog, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QRadioButton, QButtonGroup, QCheckBox, QComboBox,
    QLineEdit, QFileDialog, QMessageBox, QScrollArea, QFrame, QSizePolicy, QToolButton
)
from PySide6.QtCore import Qt, Signal, QSize, QRectF
from PySide6.QtGui import QFont, QIcon, QColor, QPixmap, QPainter

from engine.companion_store import get_companion_store, CompanionStore
from engine.companion_assets import CompanionAssetManager, BUILTIN_COMPANIONS
from engine.preference_learning import get_learning_engine, PreferenceLearningEngine
from engine.personalization import PersonalizationEngine
from ui.companion_preview import CompanionPreviewWidget
from ui.companion_renderer import CompanionRenderer
from ui.workspace_style import workspace_style, label, surface, harmonize_legacy_styles, guard_wheel_events

class CompanionStudioDialog(QDialog):
    applied = Signal(dict)

    def __init__(self, parent=None, embedded: bool = False):
        super().__init__(parent)
        self.embedded = embedded
        if embedded:
            self.setWindowFlags(Qt.Widget)
        self.setWindowTitle("FlowPilot Companion Studio")
        self.resize(1000, 740)
        self.setMinimumSize(680, 500)

        self.store: CompanionStore = get_companion_store()
        self.assets: CompanionAssetManager = CompanionAssetManager()
        self.learning: PreferenceLearningEngine = get_learning_engine()
        self.personalization: PersonalizationEngine = PersonalizationEngine()

        # Working draft configuration
        self._draft: Dict[str, Any] = self.store.get_all()
        from engine.config import load_config
        parent_config = getattr(parent, "config", None)
        self._theme = (parent_config if isinstance(parent_config, dict) else load_config()).get("ui_theme", "sand")

        self._init_styles()
        self._init_ui()
        self._load_draft_into_ui()
        harmonize_legacy_styles(self, self._theme, include_root=False)
        guard_wheel_events(self)

    def _init_styles(self):
        self.setObjectName("WorkspacePage")
        self.setStyleSheet(workspace_style(self._theme))

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 26, 28, 22)
        main_layout.setSpacing(16)

        # Header
        main_layout.addWidget(label("Companion Studio", "title"))
        main_layout.addWidget(label("A little personality for your workspace. Entirely yours."))

        # Tabs
        self.tabs = QTabWidget(self)
        self.tab_library = self._build_library_tab()
        self.tab_create = self._build_create_tab()
        
        try:
            from ui.pixel_creator import PixelCreatorWidget
            self.tab_pixel_creator = PixelCreatorWidget(self)
            self.tab_pixel_creator.companion_created.connect(self._on_pixel_companion_created)
        except Exception as e:
            print(f"[CompanionStudio] Pixel creator deferred: {e}")
            self.tab_pixel_creator = None

        self.tab_behavior = self._build_behavior_tab()
        self.tab_memory = self._build_memory_tab()

        self.tabs.addTab(self.tab_library, "Library")
        if self.tab_pixel_creator:
            self.tabs.addTab(self.tab_pixel_creator, "Pixel editor")
        self.tabs.addTab(self.tab_create, "Import")
        self.tabs.addTab(self.tab_behavior, "Motion")
        self.tabs.addTab(self.tab_memory, "Learning")
        main_layout.addWidget(self.tabs, stretch=1)

        # Footer Actions
        footer = QHBoxLayout()
        self.btn_show_live = QPushButton("Show on desktop")
        self.btn_show_live.clicked.connect(self._on_show_live_clicked)
        footer.addWidget(self.btn_show_live)
        self.apply_status = label("Preview only")
        footer.addWidget(self.apply_status)
        footer.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        footer.addWidget(self.btn_cancel)

        self.btn_apply = QPushButton("Apply Changes")
        self.btn_apply.setObjectName("primaryBtn")
        self.btn_apply.clicked.connect(self._on_apply_clicked)
        footer.addWidget(self.btn_apply)

        main_layout.addLayout(footer)

    # -------------------------------------------------------------
    # Tab 1: Library & Selection
    # -------------------------------------------------------------
    def _build_library_tab(self) -> QWidget:
        widget = QWidget()
        widget.setObjectName("WorkspacePage")
        widget.setMinimumHeight(500)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 16, 0, 0)
        layout.setSpacing(22)

        left_box = QVBoxLayout()
        left_box.addWidget(label("Find your desk companion", "section"))
        left_box.addWidget(label("Choose a character. Preview it before applying."))
        self.search_companions = QLineEdit()
        self.search_companions.setPlaceholderText("Search your companions")
        self.search_companions.setAccessibleName("Search companions")
        self.search_companions.textChanged.connect(self._filter_companions)
        left_box.addWidget(self.search_companions)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.comp_list_container = QWidget()
        self.comp_list_container.setObjectName("WorkspacePage")
        self.comp_list_layout = QGridLayout(self.comp_list_container)
        self.comp_list_layout.setSpacing(10)
        self.comp_list_layout.setContentsMargins(0, 4, 8, 4)
        self.comp_btn_group = QButtonGroup(self)
        self.comp_btn_group.buttonClicked.connect(self._on_companion_selected)
        scroll.setWidget(self.comp_list_container)
        left_box.addWidget(scroll, 1)
        self.no_results = label("No companions match your search.")
        self.no_results.hide()
        left_box.addWidget(self.no_results)
        self.chk_lock = QCheckBox("Lock appearance")
        self.chk_lock.setToolTip("Prevent accidental appearance changes from desktop gestures.")
        self.chk_lock.setChecked(True)
        self.chk_lock.toggled.connect(self._on_lock_toggled)
        left_box.addWidget(self.chk_lock)
        layout.addLayout(left_box, 3)

        stage, right_box = surface()
        stage.setMinimumWidth(260)
        right_box.addWidget(label("PREVIEW ONLY · NO MICROPHONE", "eyebrow"))
        self.preview_widget = CompanionPreviewWidget()
        self.preview_widget.setFixedSize(200, 200)
        self.preview_widget.setAccessibleName("Selected companion animation preview")
        right_box.addWidget(self.preview_widget, alignment=Qt.AlignCenter)
        self.lbl_comp_name = label("", "section")
        right_box.addWidget(self.lbl_comp_name)
        self.lbl_comp_desc = label("")
        right_box.addWidget(self.lbl_comp_desc)
        right_box.addWidget(label("Try a dictation state", "eyebrow"))
        self.preview_state = QComboBox()
        for title, state in (("Resting", "idle"), ("Listening", "listening"),
                             ("Processing", "processing"), ("Confirmed delivery", "success"),
                             ("Sent — unverified", "unverified"), ("Recovery needed", "recovery")):
            self.preview_state.addItem(title, state)
        self.preview_state.currentIndexChanged.connect(
            lambda _: self.preview_widget.set_preview_state(self.preview_state.currentData()))
        right_box.addWidget(self.preview_state)
        right_box.addWidget(label("These animations are simulated. Nothing is recorded or pasted."))
        self.btn_delete_custom = QPushButton("Delete custom creation")
        self.btn_delete_custom.setStyleSheet("color: #F87171;")
        self.btn_delete_custom.clicked.connect(self._on_delete_custom_clicked)
        self.btn_delete_custom.hide()
        right_box.addWidget(self.btn_delete_custom)
        right_box.addStretch()
        layout.addWidget(stage, 2)
        outer = QScrollArea()
        outer.setWidgetResizable(True)
        outer.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer.setWidget(widget)
        return outer

    def _refresh_companion_list(self):
        for btn in self.comp_btn_group.buttons():
            self.comp_btn_group.removeButton(btn)
        while self.comp_list_layout.count():
            item = self.comp_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        selected_id = self._draft.get("selected_asset_id", "kitty")
        for idx, comp in enumerate(self.assets.list_all_companions()):
            name = comp.get("name", comp["id"]).replace(" (Prototype)", "")
            button = QToolButton()
            button.setProperty("role", "companionTile")
            button.setProperty("comp_id", comp["id"])
            button.setProperty("search_text", name.casefold())
            short_names = {"kiki": "Kiki", "kitty": "Pixel Kitty", "dog": "Pixel Pup",
                           "mascot": "Pilot", "seedling": "Seedling", "nimbus": "Nimbus",
                           "signal": "Signal", "wave_bar": "Sound waves", "edge_line": "Docked line"}
            title = short_names.get(comp["id"], name)
            button.setText(title if len(title) <= 19 else title[:17] + "…")
            button.setAccessibleName(name)
            button.setToolTip(comp.get("description", name))
            button.setCheckable(True)
            button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            button.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
            button.setMinimumHeight(144)
            pixmap = QPixmap(88, 88)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            try:
                CompanionRenderer.render(
                    painter, QRectF(8, 8, 72, 72), comp["id"], "idle", 0, 0,
                    palette=self._draft.get("cat_palette", "orange tabby"),
                    reduced_motion=True, is_preview=True,
                    custom_data=comp if comp.get("type") != "builtin" else None)
            finally:
                painter.end()
            button.setIcon(QIcon(pixmap))
            button.setIconSize(QSize(88, 88))
            button.setChecked(comp["id"] == selected_id)
            self.comp_btn_group.addButton(button, idx)
            self.comp_list_layout.addWidget(button, idx // 2, idx % 2)
        self._filter_companions(self.search_companions.text())
        self._update_preview_from_draft()

    def _filter_companions(self, query):
        visible = 0
        for button in self.comp_btn_group.buttons():
            self.comp_list_layout.removeWidget(button)
            matches = query.casefold().strip() in button.property("search_text")
            button.setVisible(matches)
            if matches:
                self.comp_list_layout.addWidget(button, visible // 2, visible % 2)
                visible += 1
        self.no_results.setVisible(visible == 0)

    # -------------------------------------------------------------
    # Tab 2: Create Custom Companion
    # -------------------------------------------------------------
    def _build_create_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Mode Selection
        mode_box = QHBoxLayout()
        mode_label = QLabel("Creation Type:")
        mode_label.setStyleSheet("font-weight: bold;")
        mode_box.addWidget(mode_label)

        self.rb_mode_emoji = QRadioButton("Unicode Emoji")
        self.rb_mode_emoji.setChecked(True)
        self.rb_mode_emoji.toggled.connect(self._on_create_mode_changed)
        mode_box.addWidget(self.rb_mode_emoji)

        self.rb_mode_image = QRadioButton("Transparent PNG / Sprite")
        mode_box.addWidget(self.rb_mode_image)
        mode_box.addStretch()
        layout.addLayout(mode_box)

        # Emoji Container
        self.container_emoji = QFrame()
        emoji_layout = QVBoxLayout(self.container_emoji)
        emoji_layout.setContentsMargins(0, 0, 0, 0)
        emoji_layout.setSpacing(10)

        row_e1 = QHBoxLayout()
        row_e1.addWidget(QLabel("Emoji Glyph:"))
        self.txt_emoji = QLineEdit("🐱")
        self.txt_emoji.setFixedWidth(80)
        self.txt_emoji.setAlignment(Qt.AlignCenter)
        self.txt_emoji.setFont(QFont("Segoe UI Emoji", 16))
        row_e1.addWidget(self.txt_emoji)

        row_e1.addWidget(QLabel("Companion Name:"))
        self.txt_emoji_name = QLineEdit("My Space Kitty")
        row_e1.addWidget(self.txt_emoji_name)
        emoji_layout.addLayout(row_e1)

        btn_save_emoji = QPushButton("Save Emoji Companion to Library")
        btn_save_emoji.setObjectName("primaryBtn")
        btn_save_emoji.clicked.connect(self._on_save_emoji_clicked)
        emoji_layout.addWidget(btn_save_emoji)
        layout.addWidget(self.container_emoji)

        # Image Container
        self.container_image = QFrame()
        self.container_image.hide()
        img_layout = QVBoxLayout(self.container_image)
        img_layout.setContentsMargins(0, 0, 0, 0)
        img_layout.setSpacing(10)

        row_i1 = QHBoxLayout()
        self.btn_browse_img = QPushButton("Choose Transparent PNG...")
        self.btn_browse_img.clicked.connect(self._on_browse_image)
        row_i1.addWidget(self.btn_browse_img)
        self.lbl_img_path = QLabel("No file selected")
        self.lbl_img_path.setStyleSheet("color: #94A3B8;")
        row_i1.addWidget(self.lbl_img_path)
        img_layout.addLayout(row_i1)

        row_i2 = QHBoxLayout()
        row_i2.addWidget(QLabel("Name:"))
        self.txt_img_name = QLineEdit("Custom Mascot")
        row_i2.addWidget(self.txt_img_name)
        img_layout.addLayout(row_i2)

        btn_save_img = QPushButton("Import Image Companion to Library")
        btn_save_img.setObjectName("primaryBtn")
        btn_save_img.clicked.connect(self._on_save_image_clicked)
        img_layout.addWidget(btn_save_img)
        layout.addWidget(self.container_image)

        layout.addSeparator() if hasattr(layout, "addSeparator") else None

        # Export / Import Package (.flowpack)
        pack_box = QHBoxLayout()
        pack_label = QLabel("Companion Packages (.flowpack):")
        pack_label.setStyleSheet("color: #94A3B8;")
        pack_box.addWidget(pack_label)

        btn_import_pack = QPushButton("Import Package (.flowpack)")
        btn_import_pack.clicked.connect(self._on_import_pack_clicked)
        pack_box.addWidget(btn_import_pack)

        btn_export_pack = QPushButton("Export Selected Package")
        btn_export_pack.clicked.connect(self._on_export_pack_clicked)
        pack_box.addWidget(btn_export_pack)
        pack_box.addStretch()
        layout.addLayout(pack_box)

        layout.addStretch()
        return widget

    # -------------------------------------------------------------
    # Tab 3: Behavior & Motion
    # -------------------------------------------------------------
    def _build_behavior_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        visibility_row = QHBoxLayout()
        visibility_row.addWidget(QLabel("Desktop visibility:"))
        self.combo_visibility = QComboBox()
        for title, value in (("Smart (hide for fullscreen and presentations)", "smart"),
                             ("Always show", "always"), ("Hide until I show it", "hidden")):
            self.combo_visibility.addItem(title, value)
        self.combo_visibility.setAccessibleName("Desktop companion visibility")
        self.combo_visibility.currentIndexChanged.connect(
            lambda _: self._draft.__setitem__("visibility_mode", self.combo_visibility.currentData()))
        visibility_row.addWidget(self.combo_visibility, 1)
        layout.addLayout(visibility_row)
        visibility_hint = QLabel("Smart can hide the pet on any monitor. Dictation still works from the tray and hotkey.")
        visibility_hint.setWordWrap(True)
        layout.addWidget(visibility_hint)

        # Motion Preset Dropdown
        m_row = QHBoxLayout()
        m_row.addWidget(QLabel("Motion Preset:"))
        self.combo_motion = QComboBox()
        self.combo_motion.addItems([
            "Gentle Bob (Subtle floating oscillation)",
            "Breathe (Smooth scale expansion)",
            "Tiny Tilt (Playful gentle rotation)",
            "Audio Pulse (Reactions to spoken decibels)",
            "Celebration (Cheerful bounce on text paste)",
            "Reduced Motion (Static presentation)"
        ])
        self.combo_motion.currentIndexChanged.connect(self._on_motion_changed)
        m_row.addWidget(self.combo_motion, stretch=1)
        layout.addLayout(m_row)

        # Kitty Fur Color Palette
        p_row = QHBoxLayout()
        p_row.addWidget(QLabel("Companion Color Palette:"))
        self.combo_palette = QComboBox()
        palettes = [
            ("Orange Tabby", "orange tabby"),
            ("Calico", "calico"),
            ("Midnight Black", "black"),
            ("Classic Gray", "gray"),
            ("Siamese", "siamese"),
            ("Pastel Pink", "pink"),
            ("Snow White", "white"),
            ("Mint", "mint"),
            ("Chocolate", "chocolate"),
            ("Cream", "cream"),
            ("Kiki: Autumn Ember", "autumn"),
            ("Kiki: Cerulean Frost", "frost"),
            ("Kiki: Matcha Spring", "matcha"),
        ]
        for label, val in palettes:
            self.combo_palette.addItem(label, val)
        self.combo_palette.currentIndexChanged.connect(self._on_palette_changed)
        p_row.addWidget(self.combo_palette, stretch=1)
        layout.addLayout(p_row)

        # Sound effects
        self.chk_sound = QCheckBox("Enable Kitty Sound Effects (Meow on dictation start/paste)")
        self.chk_sound.toggled.connect(self._on_sound_toggled)
        layout.addWidget(self.chk_sound)

        # Snap Position Controls
        pos_box = QVBoxLayout()
        pos_label = QLabel("Quick Desktop Snap Positions:")
        pos_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        pos_box.addWidget(pos_label)

        grid = QGridLayout()
        grid.setSpacing(8)
        positions = [
            ("Top-Left", "top_left"),
            ("Top-Right", "top_right"),
            ("Bottom-Left", "bottom_left"),
            ("Bottom-Right (Default)", "bottom_right"),
            ("Right-Edge", "right_edge"),
            ("Bottom-Center", "bottom_center")
        ]
        for i, (name, tag) in enumerate(positions):
            b = QPushButton(name)
            b.clicked.connect(lambda _, t=tag: self._on_snap_position(t))
            grid.addWidget(b, i // 2, i % 2)
        pos_box.addLayout(grid)
        layout.addLayout(pos_box)

        layout.addStretch()
        return widget

    # -------------------------------------------------------------
    # Tab 4: Memory & Preference Learning
    # -------------------------------------------------------------
    def _build_memory_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # Opt-in learning toggle
        self.chk_learning = QCheckBox("Enable Adaptive Preference Learning (Zero-surveillance, 3-day consensus)")
        self.chk_learning.setChecked(self.learning.is_enabled())
        self.chk_learning.toggled.connect(self._on_learning_toggled)
        layout.addWidget(self.chk_learning)

        desc = QLabel("FlowPilot learns only from your deliberate settings choices per app. No keystrokes, clipboard, or audio are ever recorded.")
        desc.setStyleSheet("color: #94A3B8; font-size: 11px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        app_row = QHBoxLayout()
        self.txt_visibility_app = QLineEdit()
        self.txt_visibility_app.setPlaceholderText("Application name, e.g. code.exe")
        self.txt_visibility_app.setAccessibleName("Application executable name")
        app_row.addWidget(self.txt_visibility_app)
        self.combo_app_visibility = QComboBox()
        for title, value in (("Normal", "normal"), ("Quiet edge", "edge"), ("Hidden", "hidden")):
            self.combo_app_visibility.addItem(title, value)
        self.combo_app_visibility.setAccessibleName("Companion appearance in this application")
        app_row.addWidget(self.combo_app_visibility)
        save_app_rule = QPushButton("Save app rule")
        save_app_rule.clicked.connect(self._on_save_app_visibility)
        app_row.addWidget(save_app_rule)
        layout.addLayout(app_row)

        # Proposals & Rules Section
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        mem_container = QWidget()
        self.mem_layout = QVBoxLayout(mem_container)
        self.mem_layout.setSpacing(10)
        scroll.setWidget(mem_container)
        layout.addWidget(scroll, stretch=1)

        # Teach a Word Section
        vocab_box = QVBoxLayout()
        vocab_title = QLabel("Teach a Word (Custom Vocabulary Alias):")
        vocab_title.setStyleSheet("font-weight: bold; color: #38BDF8; margin-top: 8px;")
        vocab_box.addWidget(vocab_title)

        v_row = QHBoxLayout()
        self.txt_term = QLineEdit()
        self.txt_term.setPlaceholderText("Canonical Term (e.g. FlowPilot)")
        v_row.addWidget(self.txt_term)

        self.txt_alias = QLineEdit()
        self.txt_alias.setPlaceholderText("Phonetic Alias (e.g. flow pilot)")
        v_row.addWidget(self.txt_alias)

        btn_add_vocab = QPushButton("Teach Term")
        btn_add_vocab.clicked.connect(self._on_add_vocab_clicked)
        v_row.addWidget(btn_add_vocab)
        vocab_box.addLayout(v_row)
        layout.addLayout(vocab_box)

        # Clear All Learning
        btn_clear_learning = QPushButton("Clear All Learned Data")
        btn_clear_learning.setStyleSheet("color: #F87171; border-color: #7F1D1D;")
        btn_clear_learning.clicked.connect(self._on_clear_learning_clicked)
        layout.addWidget(btn_clear_learning)

        self._refresh_memory_tab()
        return widget

    def _refresh_memory_tab(self):
        # Clear existing items
        while self.mem_layout.count():
            item = self.mem_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Render Proposals
        proposals = self.learning.get_proposals()
        if proposals:
            p_header = QLabel("Pending App Proposals (Requires Your Approval):")
            p_header.setStyleSheet("font-weight: bold; color: #F59E0B;")
            self.mem_layout.addWidget(p_header)

            for prop in proposals:
                card = QFrame()
                card.setStyleSheet("background-color: #0F172A; border: 1px solid #F59E0B; border-radius: 6px; padding: 6px;")
                c_lay = QHBoxLayout(card)
                info = QLabel(f"Application: <b>{prop['app_id']}</b><br>Setting: <b>{prop['setting_key']}</b> -> <i>{prop['value']}</i><br><small>{prop['days_observed']} days observed ({prop['consensus_pct']}% consensus)</small>")
                c_lay.addWidget(info, stretch=1)

                btn_acc = QPushButton("Accept")
                btn_acc.setStyleSheet("background-color: #16A34A; color: white;")
                btn_acc.clicked.connect(lambda _, p=prop: self._on_accept_prop(p))
                c_lay.addWidget(btn_acc)

                btn_dis = QPushButton("Dismiss")
                btn_dis.clicked.connect(lambda _, p=prop: self._on_dismiss_prop(p, False))
                c_lay.addWidget(btn_dis)

                btn_never = QPushButton("Never Suggest")
                btn_never.setStyleSheet("color: #F87171;")
                btn_never.clicked.connect(lambda _, p=prop: self._on_dismiss_prop(p, True))
                c_lay.addWidget(btn_never)
                self.mem_layout.addWidget(card)

        # Render Active Rules
        rules = self.learning.get_approved_rules()
        r_header = QLabel("Active Learned App Rules:")
        r_header.setStyleSheet("font-weight: bold; color: #38BDF8; margin-top: 6px;")
        self.mem_layout.addWidget(r_header)

        if not rules:
            none_lbl = QLabel("No active learned rules. Deliberate settings choices will appear here once approved.")
            none_lbl.setStyleSheet("color: #94A3B8; font-style: italic;")
            self.mem_layout.addWidget(none_lbl)
        else:
            for app_id, app_rules in rules.items():
                for k, v in app_rules.items():
                    r_card = QFrame()
                    r_card.setStyleSheet("background-color: #0F172A; border: 1px solid #334155; border-radius: 6px; padding: 4px;")
                    r_lay = QHBoxLayout(r_card)
                    r_lay.addWidget(QLabel(f"App <b>{app_id}</b>: {k} = <i>{v}</i>"), stretch=1)
                    btn_forget = QPushButton("Forget Rule")
                    btn_forget.setStyleSheet("color: #F87171;")
                    btn_forget.clicked.connect(lambda _, a=app_id, sk=k: self._on_forget_rule(a, sk))
                    r_lay.addWidget(btn_forget)
                    self.mem_layout.addWidget(r_card)

        self.mem_layout.addStretch()

    # -------------------------------------------------------------
    # State Synchronization & UI Callbacks
    # -------------------------------------------------------------
    def _load_draft_into_ui(self):
        self._draft = self.store.get_all()
        visibility_index = self.combo_visibility.findData(self._draft.get("visibility_mode", "smart"))
        self.combo_visibility.setCurrentIndex(max(0, visibility_index))
        self.chk_lock.setChecked(self._draft.get("appearance_locked", True))
        self.chk_sound.setChecked(self._draft.get("cat_sound", True))

        # Select motion preset
        preset = self._draft.get("motion_preset", "gentle_bob")
        preset_map = {
            "gentle_bob": 0, "breathe": 1, "tiny_tilt": 2,
            "audio_pulse": 3, "celebration": 4, "reduced_motion": 5
        }
        self.combo_motion.setCurrentIndex(preset_map.get(preset, 0))

        # Select palette
        palette = self._draft.get("cat_palette", "orange tabby")
        idx = self.combo_palette.findData(palette)
        if idx >= 0:
            self.combo_palette.setCurrentIndex(idx)

        self._refresh_companion_list()

    def _update_preview_from_draft(self):
        comp_id = self._draft.get("selected_asset_id", "kitty")
        comp = self.assets.get_companion_by_id(comp_id) or {"id": "kitty", "type": "builtin"}
        palette = self._draft.get("cat_palette", "orange tabby")
        preset = self._draft.get("motion_preset", "gentle_bob")
        reduced = self._draft.get("reduced_motion", False)

        self.preview_widget.set_companion(comp, palette=palette, motion_preset=preset, reduced_motion=reduced)
        self.lbl_comp_name.setText(comp.get("name", comp_id).replace(" (Prototype)", ""))
        self.lbl_comp_desc.setText(comp.get("description", comp.get("name", "")))

        # Show delete button only for custom creations
        if comp.get("type") != "builtin":
            self.btn_delete_custom.show()
        else:
            self.btn_delete_custom.hide()

    def _on_companion_selected(self, button: QRadioButton):
        comp_id = button.property("comp_id")
        self._draft["selected_asset_id"] = comp_id
        self._update_preview_from_draft()

    def _on_lock_toggled(self, checked: bool):
        self._draft["appearance_locked"] = bool(checked)

    def _on_motion_changed(self, index: int):
        presets = ["gentle_bob", "breathe", "tiny_tilt", "audio_pulse", "celebration", "reduced_motion"]
        chosen = presets[index] if index < len(presets) else "gentle_bob"
        self._draft["motion_preset"] = chosen
        self._draft["reduced_motion"] = (chosen == "reduced_motion")
        self._update_preview_from_draft()

    def _on_palette_changed(self, index: int):
        val = self.combo_palette.itemData(index)
        if val:
            self._draft["cat_palette"] = val
            self._update_preview_from_draft()

    def _on_sound_toggled(self, checked: bool):
        self._draft["cat_sound"] = bool(checked)

    def _on_snap_position(self, corner: str):
        self._draft["snap_corner"] = corner
        QMessageBox.information(self, "Position Set", f"Companion will snap to '{corner}' upon Apply.")

    def _on_create_mode_changed(self, is_emoji: bool):
        if is_emoji:
            self.container_emoji.show()
            self.container_image.hide()
        else:
            self.container_emoji.hide()
            self.container_image.show()

    def _on_save_emoji_clicked(self):
        glyph = self.txt_emoji.text().strip()
        name = self.txt_emoji_name.text().strip() or f"Emoji {glyph}"
        if not glyph:
            QMessageBox.warning(self, "Invalid Emoji", "Please enter a valid Unicode emoji character.")
            return

        preset = self._draft.get("motion_preset", "gentle_bob")
        comp = self.assets.create_emoji_companion(name, glyph, motion_preset=preset)
        self._draft["selected_asset_id"] = comp["id"]
        self._refresh_companion_list()
        self.tabs.setCurrentIndex(0)  # Jump back to Library
        QMessageBox.information(self, "Companion Created", f"Successfully saved emoji companion '{name}'.")

    def _on_browse_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Choose Transparent PNG", "", "PNG Images (*.png)"
        )
        if file_path:
            self._selected_img_file = Path(file_path)
            self.lbl_img_path.setText(self._selected_img_file.name)

    def _on_save_image_clicked(self):
        if not hasattr(self, "_selected_img_file") or not self._selected_img_file.exists():
            QMessageBox.warning(self, "Missing Image", "Please select a valid transparent PNG file first.")
            return

        name = self.txt_img_name.text().strip() or self._selected_img_file.stem
        try:
            preset = self._draft.get("motion_preset", "gentle_bob")
            comp = self.assets.create_image_companion(name, self._selected_img_file, motion_preset=preset)
            self._draft["selected_asset_id"] = comp["id"]
            self._refresh_companion_list()
            self.tabs.setCurrentIndex(0)
            QMessageBox.information(self, "Companion Created", f"Successfully created image companion '{name}'.")
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to import image: {e}")

    def _on_export_pack_clicked(self):
        comp_id = self._draft.get("selected_asset_id")
        comp = self.assets.get_companion_by_id(comp_id)
        if not comp or comp.get("type") == "builtin":
            QMessageBox.information(self, "Export Info", "Built-in companions cannot be exported. Select a custom creation to export.")
            return

        dest_file, _ = QFileDialog.getSaveFileName(self, "Export Companion Package", f"{comp_id}.flowpack", "FlowPack (*.flowpack)")
        if dest_file:
            try:
                self.assets.export_companion_pack(comp_id, Path(dest_file))
                QMessageBox.information(self, "Export Complete", f"Successfully exported {dest_file}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export: {e}")

    def _on_import_pack_clicked(self):
        src_file, _ = QFileDialog.getOpenFileName(self, "Import Companion Package", "", "FlowPack (*.flowpack)")
        if src_file:
            try:
                comp = self.assets.import_companion_pack(Path(src_file))
                self._draft["selected_asset_id"] = comp["id"]
                self._refresh_companion_list()
                QMessageBox.information(self, "Import Complete", f"Imported companion '{comp.get('name')}' successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Import Error", f"Failed to import package: {e}")

    def _on_delete_custom_clicked(self):
        comp_id = self._draft.get("selected_asset_id")
        comp = self.assets.get_companion_by_id(comp_id)
        if not comp or comp.get("type") == "builtin":
            return

        resp = QMessageBox.question(
            self, "Delete Creation", f"Are you sure you want to delete '{comp.get('name')}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if resp == QMessageBox.Yes:
            self.assets.delete_companion(comp_id)
            self._draft["selected_asset_id"] = "kitty"
            self._refresh_companion_list()

    def _on_learning_toggled(self, checked: bool):
        self.learning.set_enabled(checked)
        self._refresh_memory_tab()

    def _on_accept_prop(self, prop: Dict[str, Any]):
        self.learning.accept_proposal(prop)
        self._refresh_memory_tab()

    def _on_dismiss_prop(self, prop: Dict[str, Any], never: bool):
        self.learning.dismiss_proposal(prop, never_suggest=never)
        self._refresh_memory_tab()

    def _on_forget_rule(self, app_id: str, setting_key: str):
        self.learning.forget_rule(app_id, setting_key)
        self._refresh_memory_tab()
        self.applied.emit({"action": "rule_changed"})

    def _on_save_app_visibility(self):
        app_name = self.txt_visibility_app.text().strip().lower()
        if not app_name.endswith(".exe") or any(c in app_name for c in "\\/:"):
            QMessageBox.warning(self, "Invalid application", "Enter an executable name such as code.exe.")
            return
        try:
            self.learning.set_approved_rule(app_name, "companion_visibility", self.combo_app_visibility.currentData())
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Invalid rule", str(exc))
            return
        self.txt_visibility_app.clear()
        self._refresh_memory_tab()
        self.applied.emit({"action": "rule_changed"})

    def _on_clear_learning_clicked(self):
        resp = QMessageBox.question(
            self, "Clear Learning Data",
            "Are you sure you want to completely erase all learned app rules and proposals?",
            QMessageBox.Yes | QMessageBox.No
        )
        if resp == QMessageBox.Yes:
            self.learning.clear_all_learning_data()
            self._refresh_memory_tab()

    def _on_add_vocab_clicked(self):
        term = self.txt_term.text().strip()
        alias = self.txt_alias.text().strip()
        if not term:
            QMessageBox.warning(self, "Input Required", "Please enter a canonical term.")
            return

        # FactGuard invariant protection check:
        # Vocabulary alias cannot be numbers, dates, or critical negations
        negations = {"not", "no", "never", "cannot", "won't", "don't"}
        if alias.lower() in negations or any(c.isdigit() for c in alias):
            QMessageBox.critical(self, "FactGuard Protection", "Vocabulary alias cannot alter numbers or critical negations.")
            return

        self.personalization.add_term(term, alias)
        self.txt_term.clear()
        self.txt_alias.clear()
        QMessageBox.information(self, "Term Saved", f"Taught '{term}' (alias: '{alias or term}').")

    def _on_show_live_clicked(self):
        # Notify parent app to show and raise companion
        self.applied.emit({"action": "show_live"})

    def _on_apply_clicked(self):
        # Atomically commit draft to CompanionStore
        try:
            updated = self.store.update(self._draft)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Could not save companion", str(exc))
            return
        self.applied.emit(updated)
        if self.embedded:
            self.apply_status.setText("Companion changes applied.")
        else:
            self.accept()

    def _on_pixel_companion_created(self, manifest: dict):
        self._refresh_companion_list()
        self._draft = self.store.get_all()
        self.applied.emit(self._draft)

    def reject(self):
        # Discard unapplied draft and reload state from store
        self._draft = self.store.get_all()
        self._load_draft_into_ui()
        if self.embedded:
            self.rejected.emit()
        else:
            super().reject()

    def showEvent(self, event):
        super().showEvent(event)
        self._draft = self.store.get_all()
        self._load_draft_into_ui()
        self._refresh_memory_tab()

    def closeEvent(self, event):
        self.preview_widget._anim_timer.stop()
        if hasattr(self, "tab_pixel_creator") and self.tab_pixel_creator:
            try:
                self.tab_pixel_creator.close()
            except Exception:
                pass
        super().closeEvent(event)



