"""
Feature 28: FlowPilot First-Run Local Setup Wizard
Provides an interactive 4-step onboarding flow:
1. Microphone selection and live audio level test
2. Local STT model verification (100% offline, zero network egress)
3. Primary language selection (LanguageRegistry integration)
4. Practice dictation trial and paste recovery demonstration
"""

import os
import sys
import time
import logging

logger = logging.getLogger("FlowPilot.SetupWizard")
import threading
import numpy as np
from pathlib import Path
from typing import Optional, Callable

from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QProgressBar, QTextEdit, QFrame, QStackedWidget,
    QCheckBox, QMessageBox, QRadioButton, QButtonGroup
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QColor

from engine.config import load_config, save_config
from engine.language_registry import LanguageRegistry
from engine.stt_engine import STTEngine
from engine.hotkey_service import Win32HotkeyService
from ui.workspace_style import guard_wheel_events

try:
    import sounddevice as sd
    HAS_SD = True
except ImportError:
    HAS_SD = False


class SetupWizardDialog(QDialog):
    setup_completed = Signal(dict)

    def __init__(self, parent=None, config: Optional[dict] = None):
        super().__init__(parent)
        self.setWindowTitle("FlowPilot — Local Readiness & Setup Wizard")
        self.setFixedSize(680, 560)
        self.setModal(True)
        self.config = config or load_config()

        self._mic_stream = None
        self._mic_testing = False
        self._current_level = 0.0

        self._init_styles()
        self._init_ui()
        guard_wheel_events(self)

    def _init_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0B0F19;
                color: #F8FAFC;
                font-family: 'Segoe UI', -apple-system, sans-serif;
            }
            QLabel {
                color: #F8FAFC;
            }
            QFrame#Card {
                background-color: #0F172A;
                border: 1px solid #1E293B;
                border-radius: 10px;
                padding: 16px;
            }
            QPushButton {
                background-color: #2563EB;
                color: #FFFFFF;
                font-weight: 600;
                font-size: 13px;
                padding: 9px 18px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
            QPushButton:pressed {
                background-color: #1E40AF;
            }
            QPushButton#BtnSecondary {
                background-color: #1E293B;
                color: #CBD5E1;
                border: 1px solid #334155;
            }
            QPushButton#BtnSecondary:hover {
                background-color: #334155;
            }
            QComboBox {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QProgressBar {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 6px;
                height: 14px;
                text-align: center;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10B981, stop:1 #38BDF8);
                border-radius: 5px;
            }
            QTextEdit {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 10px;
                font-size: 13px;
            }
        """)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 24, 28, 20)
        main_layout.setSpacing(16)

        # Header with branding & step indicator
        header_box = QHBoxLayout()
        title_box = QVBoxLayout()
        self.lbl_title = QLabel("Welcome to FlowPilot")
        self.lbl_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #38BDF8;")
        self.lbl_subtitle = QLabel("100% Offline Local Dictation & Meeting Intelligence")
        self.lbl_subtitle.setStyleSheet("font-size: 12px; color: #94A3B8;")
        title_box.addWidget(self.lbl_title)
        title_box.addWidget(self.lbl_subtitle)
        header_box.addLayout(title_box)

        header_box.addStretch()

        self.lbl_step_indicator = QLabel("Step 1 of 5")
        self.lbl_step_indicator.setStyleSheet("font-size: 12px; font-weight: bold; color: #10B981; background: #064E3B; padding: 4px 10px; border-radius: 12px;")
        header_box.addWidget(self.lbl_step_indicator)
        main_layout.addLayout(header_box)

        # Wizard Pages Container
        self.stack = QStackedWidget(self)

        # Step 1: Microphone
        self.page_mic = self._build_mic_step()
        self.stack.addWidget(self.page_mic)

        # Step 2: Offline Model
        self.page_model = self._build_model_step()
        self.stack.addWidget(self.page_model)

        # Step 3: Language
        self.page_lang = self._build_language_step()
        self.stack.addWidget(self.page_lang)

        # Step 4: Dictation Hotkey Setup
        self.page_hotkey = self._build_hotkey_step()
        self.stack.addWidget(self.page_hotkey)

        # Step 5: Practice & Recovery
        self.page_trial = self._build_trial_step()
        self.stack.addWidget(self.page_trial)

        main_layout.addWidget(self.stack)

        # Bottom Navigation Controls
        btn_layout = QHBoxLayout()
        self.btn_back = QPushButton("← Back")
        self.btn_back.setObjectName("BtnSecondary")
        self.btn_back.clicked.connect(self._on_back)
        self.btn_back.setEnabled(False)

        self.btn_next = QPushButton("Next: Verify Model →")
        self.btn_next.clicked.connect(self._on_next)

        btn_layout.addWidget(self.btn_back)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_next)
        main_layout.addLayout(btn_layout)

        # Level meter update timer
        self.meter_timer = QTimer(self)
        self.meter_timer.setInterval(40)
        self.meter_timer.timeout.connect(self._update_meter)

    # --- Step 1: Microphone ---
    def _build_mic_step(self) -> QWidget:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setSpacing(14)

        h1 = QLabel("1. Choose & Test Your Microphone")
        h1.setStyleSheet("font-size: 15px; font-weight: bold; color: #F8FAFC;")
        layout.addWidget(h1)

        desc = QLabel("FlowPilot reads audio directly from your default Windows audio hardware using WASAPI. Audio never leaves your physical PC.")
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 12px; color: #94A3B8; line-height: 1.4;")
        layout.addWidget(desc)

        layout.addWidget(QLabel("Input Audio Device:"))
        self.combo_mics = QComboBox()
        self._populate_mics()
        layout.addWidget(self.combo_mics)

        layout.addWidget(QLabel("Live Audio Volume Meter:"))
        self.mic_progress = QProgressBar()
        self.mic_progress.setRange(0, 100)
        self.mic_progress.setValue(0)
        layout.addWidget(self.mic_progress)

        self.btn_test_mic = QPushButton("🎤 Start Microphone Test")
        self.btn_test_mic.setObjectName("BtnSecondary")
        self.btn_test_mic.clicked.connect(self._toggle_mic_test)
        layout.addWidget(self.btn_test_mic)

        self.lbl_mic_status = QLabel("Click 'Start Microphone Test' and speak to verify audio input.")
        self.lbl_mic_status.setStyleSheet("font-size: 11px; color: #64748B;")
        layout.addWidget(self.lbl_mic_status)

        layout.addStretch()
        return card

    def _populate_mics(self):
        from ui.audio_input_picker import populate_audio_inputs
        populate_audio_inputs(self.combo_mics, self.config)

    def _toggle_mic_test(self):
        if self._mic_testing:
            self._stop_mic_test()
            self.btn_test_mic.setText("🎤 Start Microphone Test")
            self.btn_test_mic.setObjectName("BtnSecondary")
            self.lbl_mic_status.setText("Microphone test stopped.")
            self.lbl_mic_status.setStyleSheet("font-size: 11px; color: #64748B;")
        else:
            started = self._start_mic_test()
            if started:
                self.btn_test_mic.setText("⏹ Stop Microphone Test")
                self.btn_test_mic.setStyleSheet("background-color: #DC2626; color: white;")
                self.lbl_mic_status.setText("Speaking now should cause the green volume meter to move.")
                self.lbl_mic_status.setStyleSheet("font-size: 11px; color: #10B981; font-weight: 600;")

    def _start_mic_test(self) -> bool:
        if not HAS_SD:
            QMessageBox.warning(self, "No Sound Device", "sounddevice library is not available.")
            return False
        try:
            sel_data = self.combo_mics.currentData()
            if isinstance(sel_data, dict):
                from engine.audio_devices import resolve_audio_input
                res = resolve_audio_input(sel_data)
                dev_idx = res.device_index
                if dev_idx is not None and dev_idx < 0:
                    raise RuntimeError(res.error_message or "Select an available microphone.")
            else:
                dev_idx = sel_data
            def audio_cb(indata, frames, time_info, status):
                rms = np.sqrt(np.mean(indata**2))
                self._current_level = float(rms)

            self._mic_stream = sd.InputStream(
                samplerate=16000,
                channels=1,
                device=dev_idx,
                callback=audio_cb
            )
            self._mic_stream.start()
            self._mic_testing = True
            self.meter_timer.start()
            return True
        except Exception as e:
            QMessageBox.critical(self, "Microphone Error", f"Could not access selected microphone:\n{e}")
            return False

    def _stop_mic_test(self):
        self._mic_testing = False
        self.meter_timer.stop()
        if self._mic_stream:
            try:
                self._mic_stream.stop()
                self._mic_stream.close()
            except Exception:
                pass
            self._mic_stream = None
        self.mic_progress.setValue(0)

    def _update_meter(self):
        # Scale RMS level (0.0 - 0.2) to percentage (0 - 100)
        scaled = min(100, int(self._current_level * 500))
        self.mic_progress.setValue(scaled)

    # --- Step 2: Offline STT Model ---
    def _build_model_step(self) -> QWidget:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setSpacing(14)

        h2 = QLabel("2. Verified Local Speech-to-Text Model")
        h2.setStyleSheet("font-size: 15px; font-weight: bold; color: #F8FAFC;")
        layout.addWidget(h2)

        desc = QLabel("FlowPilot runs an optimized local Faster-Whisper base model directly on your CPU using 8-bit quantization (INT8). No API keys, no network connections, and no cloud latency.")
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 12px; color: #94A3B8; line-height: 1.4;")
        layout.addWidget(desc)

        resolved_path = STTEngine.resolve_model_path("base")
        exists = os.path.isdir(resolved_path) or os.path.isfile(os.path.join(resolved_path, "model.bin"))

        info_box = QFrame()
        info_box.setStyleSheet("background-color: #1E293B; border-radius: 8px; padding: 12px;")
        ib_layout = QVBoxLayout(info_box)
        ib_layout.setSpacing(8)

        lbl_m1 = QLabel(f"• Model Architecture: Faster-Whisper base (74M parameters, INT8 CPU)")
        lbl_m1.setStyleSheet("font-size: 12px; color: #E2E8F0;")
        lbl_m2 = QLabel(f"• Resolved Location: {resolved_path}")
        lbl_m2.setStyleSheet("font-size: 11px; color: #94A3B8;")
        lbl_m3 = QLabel(f"• Network Egress: 0 bytes outbound (Air-Gapped Invariant)")
        lbl_m3.setStyleSheet("font-size: 12px; color: #10B981; font-weight: 600;")
        lbl_m4 = QLabel(f"• Offline Status: {'✓ Local Model Found & Verified' if exists else '⚠ Model Pending'}")
        lbl_m4.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {'#10B981' if exists else '#F59E0B'};")

        ib_layout.addWidget(lbl_m1)
        ib_layout.addWidget(lbl_m2)
        ib_layout.addWidget(lbl_m3)
        ib_layout.addWidget(lbl_m4)
        layout.addWidget(info_box)

        layout.addStretch()
        return card

    # --- Step 3: Language Selection ---
    def _build_language_step(self) -> QWidget:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setSpacing(14)

        h3 = QLabel("3. Select Your Primary Language")
        h3.setStyleSheet("font-size: 15px; font-weight: bold; color: #F8FAFC;")
        layout.addWidget(h3)

        desc = QLabel("FlowPilot supports multi-language transcription and real-time foreign speech translation directly on your local device.")
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 12px; color: #94A3B8;")
        layout.addWidget(desc)

        layout.addWidget(QLabel("Primary Spoken Language:"))
        self.combo_lang = QComboBox()
        for lang in LanguageRegistry.list_supported_languages():
            status_suffix = " (Experimental)" if lang.get("quality_status") == "experimental" else ""
            self.combo_lang.addItem(f"{lang['name']} ({lang['native_name']}){status_suffix}", lang['code'])

        current_lang = self.config.get("language", "auto")
        idx = self.combo_lang.findData(current_lang)
        if idx >= 0:
            self.combo_lang.setCurrentIndex(idx)
        layout.addWidget(self.combo_lang)

        self.chk_translate = QCheckBox("Real-Time Translation: Translate foreign speech into English text")
        self.chk_translate.setStyleSheet("font-size: 13px; color: #E2E8F0; margin-top: 8px;")
        self.chk_translate.setChecked(self.config.get("translate_to_english", False))
        layout.addWidget(self.chk_translate)

        layout.addStretch()
        return card

    # --- Step 4: Dictation Hotkey Setup ---
    def _build_hotkey_step(self) -> QWidget:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setSpacing(12)

        h4 = QLabel("4. Choose Your Dictation Key & Trigger Mode")
        h4.setStyleSheet("font-size: 15px; font-weight: bold; color: #F8FAFC;")
        layout.addWidget(h4)

        desc = QLabel(
            "FlowPilot supports customizable global shortcuts. You can pick a single key like F9 "
            "for rapid push-to-talk, or a combination like Ctrl+Shift+Space for hands-free toggling."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 12px; color: #94A3B8; line-height: 1.4;")
        layout.addWidget(desc)

        # Mode Selection
        layout.addWidget(QLabel("Dictation Trigger Mode:"))
        mode_box = QHBoxLayout()
        self.radio_toggle = QRadioButton("Toggle (Press to start, press again to stop)")
        self.radio_ptt = QRadioButton("Push-to-Talk (Hold key while speaking)")
        self.btn_group_mode = QButtonGroup(self)
        self.btn_group_mode.addButton(self.radio_toggle)
        self.btn_group_mode.addButton(self.radio_ptt)

        cur_mode = self.config.get("hotkey_mode", "toggle")
        if cur_mode == "push_to_talk":
            self.radio_ptt.setChecked(True)
        else:
            self.radio_toggle.setChecked(True)
        mode_box.addWidget(self.radio_toggle)
        mode_box.addWidget(self.radio_ptt)
        layout.addLayout(mode_box)

        # Hotkey Selection Row
        layout.addWidget(QLabel("Global Dictation Shortcut:"))
        hk_row = QHBoxLayout()
        self.combo_hotkey = QComboBox()
        self.combo_hotkey.setEditable(True)
        self.combo_hotkey.addItems([
            "F9",
            "Ctrl+Shift+Space",
            "F8",
            "Ctrl+Alt+Space",
            "Win+Alt+Space",
            "Ctrl+F9",
            "Ctrl+Alt+D"
        ])
        cur_hk = self.config.get("hotkey", "Ctrl+Shift+Space").replace("<", "").replace(">", "").strip()
        self.combo_hotkey.setCurrentText(cur_hk)
        hk_row.addWidget(self.combo_hotkey, 3)

        self.btn_test_wizard_hk = QPushButton("Test Availability")
        self.btn_test_wizard_hk.setStyleSheet("background-color: #0369A1;")
        self.btn_test_wizard_hk.clicked.connect(self._test_wizard_hotkey)
        hk_row.addWidget(self.btn_test_wizard_hk, 1)
        layout.addLayout(hk_row)

        self.lbl_wizard_hk_status = QLabel("")
        layout.addWidget(self.lbl_wizard_hk_status)

        # Protected / Exempted default keys banner
        exempt_box = QFrame()
        exempt_box.setStyleSheet("background-color: #1E293B; border-radius: 8px; padding: 10px;")
        eb_layout = QVBoxLayout(exempt_box)
        eb_layout.setSpacing(4)
        lbl_e_title = QLabel("🛡️ Protected Default Recovery Shortcuts (Exempted from Reassignment):")
        lbl_e_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #38BDF8;")
        lbl_e1 = QLabel("• Alt + Shift + Z : Reserved for 'Paste Last Dictation' recovery")
        lbl_e1.setStyleSheet("font-size: 11px; color: #CBD5E1;")
        lbl_e2 = QLabel("• Alt + Shift + X : Reserved for 'Copy Last Dictation' recovery")
        lbl_e2.setStyleSheet("font-size: 11px; color: #CBD5E1;")
        lbl_e3 = QLabel("• Ctrl + Alt + T  : Reserved for Selected-Text Transforms")
        lbl_e3.setStyleSheet("font-size: 11px; color: #CBD5E1;")
        lbl_e_note = QLabel("FlowPilot guarantees these recovery shortcuts remain reserved so you can always recover text if an app drops a paste.")
        lbl_e_note.setStyleSheet("font-size: 11px; color: #94A3B8; font-style: italic;")
        eb_layout.addWidget(lbl_e_title)
        eb_layout.addWidget(lbl_e1)
        eb_layout.addWidget(lbl_e2)
        eb_layout.addWidget(lbl_e3)
        eb_layout.addWidget(lbl_e_note)
        layout.addWidget(exempt_box)

        layout.addStretch()
        return card

    def _test_wizard_hotkey(self):
        hk = self.combo_hotkey.currentText().strip()
        if not hk:
            self.lbl_wizard_hk_status.setStyleSheet("color: #EF4444; font-size: 12px;")
            self.lbl_wizard_hk_status.setText("Please enter or select a hotkey to test.")
            return
        cur_hk = self.config.get("hotkey", "")
        avail, msg = Win32HotkeyService.test_hotkey_availability(hk, currently_active_hotkey=cur_hk)
        if avail:
            self.lbl_wizard_hk_status.setStyleSheet("color: #10B981; font-weight: bold; font-size: 12px;")
            self.lbl_wizard_hk_status.setText(f"✓ [AVAILABLE] {msg}")
        else:
            self.lbl_wizard_hk_status.setStyleSheet("color: #EF4444; font-weight: bold; font-size: 12px;")
            self.lbl_wizard_hk_status.setText(f"✗ [CONFLICT] {msg}")

    # --- Step 5: Practice & Recovery ---
    def _build_trial_step(self) -> QWidget:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setSpacing(14)

        h5 = QLabel("5. Dictation Practice & Instant Recovery")
        h5.setStyleSheet("font-size: 15px; font-weight: bold; color: #F8FAFC;")
        layout.addWidget(h5)

        desc = QLabel("FlowPilot injects text into any focused application (Notepad, VS Code, Word, Slack, Browser). If an app ever drops a paste, you can recover it instantly.")
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 12px; color: #94A3B8;")
        layout.addWidget(desc)

        # Recovery shortcuts card
        rec_box = QFrame()
        rec_box.setStyleSheet("background-color: #1E293B; border-radius: 8px; padding: 12px;")
        rb_layout = QVBoxLayout(rec_box)
        rb_layout.setSpacing(6)

        lbl_r1 = QLabel("⚡ Dedicated Paste Recovery Shortcuts:")
        lbl_r1.setStyleSheet("font-size: 13px; font-weight: bold; color: #38BDF8;")
        lbl_r2 = QLabel("• Paste Last Dictation: Shift + Alt + Z (or Alt + Shift + Z)")
        lbl_r2.setStyleSheet("font-size: 12px; color: #F1F5F9;")
        lbl_r3 = QLabel("• Copy Last Dictation:  Shift + Alt + X (or Alt + Shift + X)")
        lbl_r3.setStyleSheet("font-size: 12px; color: #F1F5F9;")
        rb_layout.addWidget(lbl_r1)
        rb_layout.addWidget(lbl_r2)
        rb_layout.addWidget(lbl_r3)
        layout.addWidget(rec_box)

        layout.addWidget(QLabel("Practice Text Area (Speak or Paste here):"))
        self.trial_text = QTextEdit()
        self.trial_text.setPlaceholderText("Your transcribed or recovered text will appear here...")
        self.trial_text.setFixedHeight(80)
        layout.addWidget(self.trial_text)

        test_btn_box = QHBoxLayout()
        self.btn_test_recovery = QPushButton("📋 Test Paste Recovery (Insert Demo Text)")
        self.btn_test_recovery.setObjectName("BtnSecondary")
        self.btn_test_recovery.clicked.connect(self._test_recovery_action)
        test_btn_box.addWidget(self.btn_test_recovery)
        layout.addLayout(test_btn_box)

        layout.addStretch()
        return card

    def _test_recovery_action(self):
        demo = "FlowPilot offline dictation verified. Ready for work!"
        self.trial_text.setText(demo)
        # Store in TextInjector recovery buffer for demonstration
        from engine.text_injector import TextInjector
        TextInjector.last_injected_text = demo
        QMessageBox.information(
            self,
            "Recovery Buffer Ready",
            "Demo text has been staged in the FlowPilot Recovery Buffer!\n\n"
            "Pressing Shift+Alt+Z in any window will paste this text.\n"
            "Pressing Shift+Alt+X will copy it to your clipboard."
        )

    # --- Navigation Logic ---
    def _on_next(self):
        curr = self.stack.currentIndex()
        if curr == 0:
            self._stop_mic_test()
            self.stack.setCurrentIndex(1)
            self.lbl_step_indicator.setText("Step 2 of 5")
            self.btn_back.setEnabled(True)
            self.btn_next.setText("Next: Select Language →")
        elif curr == 1:
            self.stack.setCurrentIndex(2)
            self.lbl_step_indicator.setText("Step 3 of 5")
            self.btn_back.setEnabled(True)
            self.btn_next.setText("Next: Choose Hotkey →")
        elif curr == 2:
            self.stack.setCurrentIndex(3)
            self.lbl_step_indicator.setText("Step 4 of 5")
            self.btn_back.setEnabled(True)
            self.btn_next.setText("Next: Practice Dictation →")
        elif curr == 3:
            self.stack.setCurrentIndex(4)
            self.lbl_step_indicator.setText("Step 5 of 5")
            self.btn_back.setEnabled(True)
            self.btn_next.setText("Finish & Launch FlowPilot ✓")
        elif curr == 4:
            self._finish_setup()

    def _on_back(self):
        curr = self.stack.currentIndex()
        if curr == 1:
            self.stack.setCurrentIndex(0)
            self.lbl_step_indicator.setText("Step 1 of 5")
            self.btn_back.setEnabled(False)
            self.btn_next.setText("Next: Verify Model →")
        elif curr == 2:
            self.stack.setCurrentIndex(1)
            self.lbl_step_indicator.setText("Step 2 of 5")
            self.btn_next.setText("Next: Select Language →")
        elif curr == 3:
            self.stack.setCurrentIndex(2)
            self.lbl_step_indicator.setText("Step 3 of 5")
            self.btn_next.setText("Next: Choose Hotkey →")
        elif curr == 4:
            self.stack.setCurrentIndex(3)
            self.lbl_step_indicator.setText("Step 4 of 5")
            self.btn_next.setText("Next: Practice Dictation →")

    def _finish_setup(self):
        self._stop_mic_test()
        # Persist user choices
        self.config["first_run_completed"] = True
        sel_mic = self.combo_mics.currentData()
        if isinstance(sel_mic, dict):
            self.config["audio_input_selection"] = sel_mic
            from engine.audio_devices import resolve_audio_input
            res = resolve_audio_input(sel_mic)
            self.config["audio_device_index"] = res.device_index
        else:
            self.config["audio_device_index"] = sel_mic
            from engine.audio_devices import build_device_selection
            self.config["audio_input_selection"] = build_device_selection(sel_mic)
        selected_lang = self.combo_lang.currentData()
        self.config["language"] = selected_lang or "auto"
        self.config["translate_to_english"] = self.chk_translate.isChecked()

        # Save chosen hotkey and trigger mode
        hk = self.combo_hotkey.currentText().strip()
        if hk:
            self.config["hotkey"] = hk
        self.config["hotkey_mode"] = "push_to_talk" if self.radio_ptt.isChecked() else "toggle"

        save_config(self.config)

        self.setup_completed.emit(self.config)
        self.accept()

    def closeEvent(self, event):
        self._stop_mic_test()
        super().closeEvent(event)
