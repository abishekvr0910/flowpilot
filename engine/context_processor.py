"""
FlowPilot Context Processor
Coordinates Writing Intelligence (Local deterministic engine) with optional Cloud LLM.
Supports two distinct modes:
- Verbatim Mode: 100% faithful transcript with sensible punctuation.
- Polished Mode: Self-corrections, filler removal, list formatting, and style adaptation.
"""

import os
from typing import Dict, Any, Optional
from engine.writing_intelligence import WritingIntelligence

class ProfileResolver:
    """
    Resolves writing profiles using deterministic precedence:
    1. Explicit session-level selection (session_mode)
    2. Per-app configuration in config['app_profiles'][process_name]
    3. Window category auto-detection (from WindowInspector)
    4. Default fallback in config['active_tone_mode']
    """
    TERMINAL_PROCESSES = {
        "cmd.exe", "powershell.exe", "windowsterminal.exe",
        "bash.exe", "wsl.exe", "alacritty.exe", "wezterm-gui.exe", "mintty.exe"
    }

    DEVELOPER_PROCESSES = {
        "code.exe", "cursor.exe", "devenv.exe", "pycharm64.exe",
        "idea64.exe", "sublime_text.exe", "notepad++.exe"
    }

    CHAT_PROCESSES = {
        "slack.exe", "teams.exe", "discord.exe", "telegram.exe", "whatsapp.exe"
    }

    EMAIL_PROCESSES = {
        "outlook.exe", "thunderbird.exe"
    }

    VALID_PROFILES = {"general", "professional", "developer", "terminal", "email", "chat", "concise", "casual", "verbatim"}

    @classmethod
    def resolve(
        cls,
        config: Dict[str, Any],
        active_window: Optional[Dict[str, Any]] = None,
        session_mode: Optional[str] = None
    ) -> str:
        # Precedence 1: Explicit session override
        if session_mode and session_mode in cls.VALID_PROFILES:
            return session_mode

        process_name = (active_window.get("process_name", "") if active_window else "").lower()

        # Precedence 2: Configured per-app mapping in config["app_profiles"]
        app_profiles = config.get("app_profiles", {})
        if process_name and process_name in app_profiles:
            configured_profile = app_profiles[process_name].lower()
            if configured_profile in cls.VALID_PROFILES:
                return configured_profile

        # Precedence 3: Auto-detect active app category
        if config.get("auto_detect_active_app", True):
            if process_name in cls.TERMINAL_PROCESSES:
                return "terminal"
            elif process_name in cls.DEVELOPER_PROCESSES:
                return "developer"
            elif process_name in cls.CHAT_PROCESSES:
                return "chat"
            elif process_name in cls.EMAIL_PROCESSES:
                return "email"

            cat = (active_window.get("category", "") if active_window else "").lower()
            if cat == "terminal":
                return "terminal"
            elif cat == "developer":
                return "developer"
            elif cat == "chat":
                return "chat"
            elif cat == "email":
                return "email"

        # Precedence 4: Default fallback
        fallback = config.get("active_tone_mode", "professional").lower()
        return fallback if fallback in cls.VALID_PROFILES else "professional"

class ContextProcessor:
    """
    Intelligent post-processor that cleans, formats, and adapts spoken text
    to the user's specific tone mode and target application without censoring.
    """

    SYSTEM_PROMPTS = {
        "professional": (
            "You are an expert speech-to-text editor. Your task is to polish raw dictated text:\n"
            "- Remove filler sounds and speech stutters (um, uh, like, you know, ah).\n"
            "- Fix capitalization, punctuation, and obvious grammar errors.\n"
            "- Resolve spoken self-corrections (e.g. 'schedule it for Tuesday — actually, Wednesday' -> 'schedule it for Wednesday').\n"
            "- PRESERVE the speaker's original intent, numbers, dates, and names exactly.\n"
            "- DO NOT summarize, paraphrase, or truncate.\n"
            "- Output ONLY the final text without quotes."
        ),
        "general": (
            "You are an expert speech-to-text editor. Your task is to polish raw dictated text:\n"
            "- Remove filler sounds and speech stutters.\n"
            "- Fix capitalization, punctuation, and obvious grammar errors.\n"
            "- PRESERVE the speaker's original intent, numbers, dates, and names exactly.\n"
            "- Output ONLY the final text without quotes."
        ),
        "terminal": (
            "You are a command line and shell interface dictation assistant:\n"
            "- Output exact, valid shell commands or paths.\n"
            "- Strictly NEVER add trailing periods, quotes, or markdown backticks.\n"
            "- Preserve CLI flags (--flag, -f) and case sensitivity.\n"
            "- Output ONLY the final command string."
        ),
        "chat": (
            "You are a casual chat message assistant:\n"
            "- Output natural conversational prose.\n"
            "- Fix typos and remove filler sounds (um, uh).\n"
            "- Do not add heavy punctuation or unnecessary trailing periods to short responses.\n"
            "- Output ONLY the final text."
        ),
        "developer": (
            "You are a developer-focused dictation assistant. The user is writing code, commands, or technical documentation:\n"
            "- Remove filler words.\n"
            "- Format technical references accurately (camelCase, snake_case, terminal commands).\n"
            "- Keep technical terms, acronyms, and variables exact.\n"
            "- Output ONLY the final polished text with no conversational filler."
        ),
        "casual": (
            "You are a speech-to-text formatter for natural, casual communication:\n"
            "- Clean up repetitive stutters and filler hesitations (um, uh).\n"
            "- Add natural punctuation and capitalization.\n"
            "- NEVER censor or replace colloquial expressions or authentic emotional tone.\n"
            "- Output ONLY the final formatted text."
        ),
        "email": (
            "You are an executive communication assistant:\n"
            "- Format the spoken stream into a crisp, well-structured business email.\n"
            "- Add clear paragraph breaks or bullet points if a list was dictated.\n"
            "- Remove conversational fillers and polish grammar.\n"
            "- Preserve key facts, requests, and deadlines.\n"
            "- Output ONLY the final text."
        ),
        "concise": (
            "You are a concise writing editor:\n"
            "- Remove filler words and wordy redundancies.\n"
            "- Keep sentences short, direct, and impactful.\n"
            "- Preserve all core facts, numbers, and deadlines.\n"
            "- Output ONLY the final text."
        )
    }

    def __init__(self, config: Dict[str, Any], personalization: Optional[Any] = None):
        self.config = config
        self.personalization = personalization
        self.local_engine = WritingIntelligence(config, personalization=personalization)

    def process(
        self,
        raw_text: str,
        active_window: Optional[Dict[str, Any]] = None,
        session_mode: Optional[str] = None,
        language: Optional[str] = None
    ) -> str:
        if not raw_text or not raw_text.strip():
            return ""

        raw_trimmed = raw_text.strip()
        style = ProfileResolver.resolve(self.config, active_window, session_mode)
        lang_str = language or self.config.get("language", "auto")

        # 1. Check for Verbatim Mode
        if style == "verbatim":
            res = self.local_engine.polish(raw_trimmed, mode="verbatim", language=lang_str)
            return res["text"]

        # 2. Apply Local Deterministic Polishing (Self-corrections, fillers, stutters, lists, tech terms, FactGuard)
        local_result = self.local_engine.polish(raw_trimmed, mode="polished", style=style, language=lang_str)
        polished_text = local_result["text"]

        # 3. Apply Voice Snippet Expansion
        if self.personalization:
            expanded, _ = self.personalization.expand_snippets(polished_text)
            if expanded:
                polished_text = expanded

        # 4. Deterministic FactGuard Semantic Verification & Zero Cloud Egress
        # Remote cloud LLM dispatch is permanently disabled to guarantee zero network egress.
        # All formatting and polishing runs 100% locally with guaranteed preservation
        # of numbers, dates, negations, and technical entities.
        return polished_text
