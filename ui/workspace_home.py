"""Native FlowPilot home page for dictation and companion controls."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QScrollArea, QComboBox

from engine.companion_assets import CompanionAssetManager
from engine.language_registry import LanguageRegistry
from engine.text_injector import TextInjector
from ui.companion_preview import CompanionPreviewWidget
from ui.workspace_style import label, surface


class WorkspaceHome(QScrollArea):
    def __init__(self, dashboard):
        super().__init__(dashboard)
        self.dashboard = dashboard
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        content.setObjectName("WorkspacePage")
        self.setWidget(content)
        self.main_layout = QVBoxLayout(content)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        test_layout = self.main_layout
        test_layout.setContentsMargins(0, 0, 0, 0)

        # Top Heading
        heading = QHBoxLayout()
        heading.addWidget(label("Your workspace", "title"))
        heading.addStretch()
        heading.addWidget(label("ON-DEVICE DICTATION", "eyebrow"))
        test_layout.addLayout(heading)

        # Hero Surface
        hero, hero_layout = surface("heroSurface")
        hero_row = QHBoxLayout()
        words = QVBoxLayout()
        words.setSpacing(12)
        words.addWidget(label("A little less typing.\nA little more flow.", "hero"))
        words.addWidget(label("Open your editor, put the cursor where you want\nto write, and use your dictation shortcut."))
        self.shortcut_label = label("", "shortcut")
        words.addWidget(self.shortcut_label)
        self.mode_label = label("")
        words.addWidget(self.mode_label)
        self.btn_dictate = QPushButton("Start dictation")
        self.btn_dictate.setObjectName("primaryBtn")
        self.btn_dictate.setEnabled(dashboard.on_dictate is not None)
        self.btn_dictate.clicked.connect(lambda: dashboard.on_dictate() if dashboard.on_dictate else None)
        self.btn_dictate.setToolTip("Use your shortcut in an external editor to dictate at its cursor.")
        words.addWidget(self.btn_dictate, alignment=Qt.AlignLeft)
        hero_row.addLayout(words, 3)

        companion = QVBoxLayout()
        companion.setAlignment(Qt.AlignCenter)
        self.preview = CompanionPreviewWidget()
        self.preview.setFixedSize(160, 160)
        self.preview.setAccessibleName("Selected companion, idle preview")
        companion.addWidget(self.preview, alignment=Qt.AlignCenter)
        self.companion_label = label("", "section")
        self.companion_label.setAlignment(Qt.AlignCenter)
        companion.addWidget(self.companion_label)
        self.visibility_label = label("Companion visibility: starting")
        self.visibility_label.setAlignment(Qt.AlignCenter)
        companion.addWidget(self.visibility_label)
        self.visibility_choice = QComboBox()
        self.visibility_choice.setAccessibleName("Desktop companion visibility")
        for title, mode in (("Smart", "smart"), ("Always show", "always"), ("Hide", "hidden")):
            self.visibility_choice.addItem(title, mode)
        self.visibility_choice.currentIndexChanged.connect(
            lambda _: dashboard.companion_visibility_requested.emit(self.visibility_choice.currentData()))
        companion.addWidget(self.visibility_choice)
        show_now = QPushButton("Show companion now")
        show_now.clicked.connect(dashboard.show_companion_requested.emit)
        companion.addWidget(show_now)
        caption = label("YOUR DESKTOP COMPANION", "eyebrow")
        caption.setAlignment(Qt.AlignCenter)
        companion.addWidget(caption)
        customize = QPushButton("Customize Appearance")
        customize.clicked.connect(lambda: dashboard._on_nav_clicked(8))
        companion.addWidget(customize)
        hero_row.addLayout(companion, 2)
        hero_layout.addLayout(hero_row)
        test_layout.addWidget(hero)

        # Details
        details = QHBoxLayout()
        self.config_label = label("")
        details.addWidget(self.config_label, 1)
        settings = QPushButton("Adjust settings")
        settings.clicked.connect(lambda: dashboard._on_nav_clicked(9))
        details.addWidget(settings)
        test_layout.addLayout(details)

        # Recovery Surface
        recovery, recovery_layout = surface()
        row = QHBoxLayout()
        row.addWidget(label("Last dictation", "section"))
        row.addStretch()
        row.addWidget(label("THIS SESSION", "eyebrow"))
        recovery_layout.addLayout(row)
        self.last_preview = label("")
        self.last_preview.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.last_preview.setMaximumHeight(76)
        recovery_layout.addWidget(self.last_preview)
        actions = QHBoxLayout()
        self.btn_paste = QPushButton("Paste last")
        self.btn_paste.setToolTip("Paste last dictation · Alt+Shift+Z")
        self.btn_paste.clicked.connect(dashboard._on_quick_paste_last)
        self.btn_copy = QPushButton("Copy text")
        self.btn_copy.setToolTip("Copy last dictation · Alt+Shift+X")
        self.btn_copy.clicked.connect(dashboard._on_quick_copy_last)
        actions.addWidget(self.btn_paste)
        actions.addWidget(self.btn_copy)
        actions.addStretch()
        recovery_layout.addLayout(actions)
        self.retention_label = label("")
        recovery_layout.addWidget(self.retention_label)
        test_layout.addWidget(recovery)

        # Quick action navigation buttons (asserted by unit tests)
        more = QHBoxLayout()
        for title, page in (("Open Scratchpad", 3), ("Open Notetaker", 4), ("View Analytics", 5)):
            button = QPushButton(title)
            button.clicked.connect(lambda checked=False, index=page: dashboard._on_nav_clicked(index))
            more.addWidget(button)
        test_layout.addLayout(more)

        self._companion_key = None
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(750)
        self._refresh_timer.timeout.connect(self.refresh)
        self.refresh()

    def refresh(self):
        config = self.dashboard.config
        hotkey = str(config.get("hotkey", "Ctrl+Shift+Space")).replace("<", "").replace(">", "")
        self.shortcut_label.setText(hotkey)
        self.btn_dictate.setText(f"Start dictation  ·  {hotkey}")
        self.mode_label.setText("Hold to speak · release to finish" if config.get("hotkey_mode") == "push_to_talk" else "Press to start · press again to finish")
        languages = {item["code"]: item["name"] for item in LanguageRegistry.list_supported_languages()}
        language = languages.get(config.get("language", "auto"), config.get("language", "auto"))
        model = config.get("local_model_size", "base")
        self.config_label.setText(f"Configured: {language}  ·  Whisper {model}  ·  Local processing")
        text = TextInjector.last_injected_text
        self.last_preview.setText((text[:360] + "…" if len(text) > 360 else text) if text else "Your next dictation will appear here. Copy it or recover a paste without speaking again.")
        self.btn_paste.setEnabled(bool(text))
        self.btn_copy.setEnabled(bool(text))
        self.retention_label.setText("Dictation history is enabled. Manage saved entries in History & audio." if config.get("save_history_text", False) else "Dictation history is off. Scratchpad and meeting notes are saved separately.")
        data = self.dashboard.store.get_all()
        mode_index = self.visibility_choice.findData(data.get("visibility_mode", "smart"))
        self.visibility_choice.blockSignals(True)
        self.visibility_choice.setCurrentIndex(max(0, mode_index))
        self.visibility_choice.blockSignals(False)
        key = (data.get("selected_asset_id", "kitty"), data.get("cat_palette", "orange tabby"), data.get("motion_preset", "gentle_bob"), data.get("reduced_motion", False))
        if key != self._companion_key:
            self._companion_key = key
            comp = CompanionAssetManager().get_companion_by_id(key[0]) or {"id": "kitty", "type": "builtin", "name": "Pixel Kitty"}
            self.preview.set_companion(comp, palette=key[1], motion_preset=key[2], reduced_motion=key[3])
            self.companion_label.setText(comp.get("name", key[0]).replace(" (Prototype)", ""))

    def set_visibility_status(self, presentation: str, reason: str):
        self.visibility_label.setText(f"Companion: {presentation} — {reason}")

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()
        self._refresh_timer.start()

    def hideEvent(self, event):
        self._refresh_timer.stop()
        super().hideEvent(event)
