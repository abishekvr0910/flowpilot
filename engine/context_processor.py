"""
FlowPilot Context Processor
Coordinates Writing Intelligence (Local deterministic engine) with optional Cloud LLM.
Supports two distinct modes:
- Verbatim Mode: 100% faithful transcript with sensible punctuation.
- Polished Mode: Self-corrections, filler removal, list formatting, and style adaptation.
"""

import os
from typing import Dict, Any, Optional
from openai import OpenAI
from engine.writing_intelligence import WritingIntelligence

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

    def process(self, raw_text: str, active_window: Optional[Dict[str, Any]] = None) -> str:
        if not raw_text or not raw_text.strip():
            return ""

        raw_trimmed = raw_text.strip()
        configured_mode = self.config.get("active_tone_mode", "professional")

        # 1. Check for Verbatim Mode
        if configured_mode == "verbatim":
            res = self.local_engine.polish(raw_trimmed, mode="verbatim")
            return res["text"]

        # 2. Determine target style
        style = configured_mode
        if self.config.get("auto_detect_active_app", True) and active_window:
            category = active_window.get("category", "general")
            if category == "developer" and configured_mode not in ("verbatim", "email"):
                style = "developer"
            elif category == "chat" and configured_mode == "email":
                style = "casual"

        # 3. Apply Local Deterministic Polishing (Self-corrections, fillers, stutters, lists, tech terms)
        local_result = self.local_engine.polish(raw_trimmed, mode="polished", style=style)
        polished_text = local_result["text"]

        # 4. Optional Cloud LLM Enhancement (Only if user configured an API key)
        provider = self.config.get("cloud_provider", "groq")
        if provider == "groq":
            api_key = self.config.get("groq_api_key") or os.environ.get("GROQ_API_KEY")
            base_url = "https://api.groq.com/openai/v1"
            model_name = "llama-3.1-8b-instant"
        else:
            api_key = self.config.get("openai_api_key") or os.environ.get("OPENAI_API_KEY")
            base_url = "https://api.openai.com/v1"
            model_name = "gpt-4o-mini"

        if not api_key:
            # Zero-dependency local return
            return polished_text

        # If API key is present, pass to cloud LLM for additional nuance
        try:
            client = OpenAI(api_key=api_key, base_url=base_url)
            system_prompt = self.SYSTEM_PROMPTS.get(style, self.SYSTEM_PROMPTS["professional"])
            user_prompt = f"Raw dictated transcript:\n{polished_text}"
            if active_window and active_window.get("title"):
                user_prompt += f"\n\nContext: Active application is '{active_window.get('process_name')}' ('{active_window.get('title')}')."

            completion = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=1000
            )
            llm_text = completion.choices[0].message.content
            return llm_text.strip() if llm_text else polished_text
        except Exception as e:
            print(f"[ContextProcessor Warning] Cloud LLM pass skipped ({e}). Using local polished text.")
            return polished_text
