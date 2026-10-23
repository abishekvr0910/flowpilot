"""
FlowPilot Selected-Text Transforms Engine (100% Offline & Private)
Wispr Flow Parity & Leapfrog:
- Instant selected-text extraction from any Windows application via Win32 clipboard readback
- Built-in deterministic intelligence presets:
    * Make Concise (tighten sentences, strip filler, preserve facts)
    * Fix Typos & Grammar (correct punctuation, spelling, casing)
    * Format as Bullet Points (convert prose into clean, structured Markdown bullets)
    * Professional Tone (polish informal speech for corporate/executive correspondence)
    * Casual Tone (make rigid prose conversational and warm)
    * Translate to English (multilingual input to clear English)
    * Custom Voice / Text Prompt (apply user-defined transformation prompt)
- FactGuard Invariant Protection: verifies critical named entities, digits, and negations
- External replacements remain unavailable until revision and selection checks exist
"""

import sys
import re
import time
import logging
import threading
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple
import pyperclip

logger = logging.getLogger("FlowPilot.Transforms")

@dataclass
class TransformResult:
    original_text: str
    candidate_text: str
    status: str  # "success" | "unchanged" | "unsupported" | "unavailable" | "blocked" | "error"
    execution_route: str  # "deterministic" | "local_llm" | "none"
    guard_status: str  # "passed" | "failed" | "not_run"
    reason_code: str
    can_apply: bool
    error_message: Optional[str] = None

    def __iter__(self):
        """
        Backwards-compatible tuple unpacking for legacy callers:
        transformed_text, factguard_passed = result
        """
        return iter((self.candidate_text, self.can_apply))

    def __getitem__(self, index):
        return (self.candidate_text, self.can_apply)[index]

# Anchored regexes for deterministic custom natural-language aliases
RE_CUSTOM_BULLETS = re.compile(
    r"^\s*(?:format|convert|make|turn)?\s*(?:this|it)?\s*(?:in\s*to|as)?\s*(?:a\s+)?(?:bullet\s+points?|bulleted\s+list|bullet\s+list|bullets)\s*$",
    re.IGNORECASE
)
RE_CUSTOM_CONCISE = re.compile(
    r"^\s*(?:make\s+(?:this|it)?\s*)?(?:concise|shorter|brief|summarize(?:\s+(?:this|it))?)\s*$",
    re.IGNORECASE
)
RE_CUSTOM_PROFESSIONAL = re.compile(
    r"^\s*(?:make\s+(?:this|it)?\s*)?(?:professional|formal|executive)(?:\s+tone)?\s*$",
    re.IGNORECASE
)
RE_CUSTOM_CASUAL = re.compile(
    r"^\s*(?:make\s+(?:this|it)?\s*)?(?:casual|friendly|relaxed)(?:\s+tone)?\s*$",
    re.IGNORECASE
)
RE_CUSTOM_GRAMMAR = re.compile(
    r"^\s*(?:fix|correct|clean(?:\s+up)?)\s*(?:the\s+)?(?:grammar|typos?|spelling)\s*$",
    re.IGNORECASE
)

try:
    import win32gui
    import win32con
    import win32api
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

from engine.writing_intelligence import FactGuard
from engine.text_injector import TextInjector, InjectionResult, InjectionStatus

PRESET_TRANSFORMS = {
    "make_concise": {
        "id": "make_concise",
        "name": "Make Concise",
        "description": "Removes fluff, passive phrasing, and redundancy while preserving all key facts.",
        "icon": "✂️"
    },
    "fix_grammar": {
        "id": "fix_grammar",
        "name": "Fix Typos & Grammar",
        "description": "Corrects typos, punctuation, capitalization, and punctuation cleanly.",
        "icon": "✨"
    },
    "bullet_points": {
        "id": "bullet_points",
        "name": "Format as Bullet Points",
        "description": "Converts thoughts, paragraphs, or lists into structured Markdown bullets.",
        "icon": "📋"
    },
    "professional": {
        "id": "professional",
        "name": "Professional Tone",
        "description": "Polishes colloquialisms into clear, professional, workplace-ready prose.",
        "icon": "💼"
    },
    "casual": {
        "id": "casual",
        "name": "Casual Tone",
        "description": "Softens stiff or overly formal language into warm, approachable phrasing.",
        "icon": "💬"
    },
    "translate_en": {
        "id": "translate_en",
        "name": "Translate to English",
        "description": "Translates multilingual speech or foreign text into natural English.",
        "icon": "🌐"
    }
}


class TransformsEngine:
    _lock = threading.RLock()

    def __init__(self):
        self._last_original_text: str = ""
        self._last_transformed_text: str = ""
        self._last_target_hwnd: Optional[int] = None
        self._history: List[Dict[str, Any]] = []
        self._last_execution_route: str = "none"
        self._last_can_apply: bool = False

    def get_last_execution_route(self) -> str:
        """Returns whether the last transform executed via 'local_llm', 'deterministic', or 'none'."""
        with self._lock:
            return self._last_execution_route

    def get_selected_text_from_active_window(self, timeout: float = 0.35) -> Optional[str]:
        """
        Captures selected text from current foreground window safely.
        Preserves original clipboard contents before and restores if no text was selected.
        """
        if not HAS_WIN32 or sys.platform != "win32":
            try:
                return pyperclip.paste()
            except Exception:
                return None

        # 1. Preserve current clipboard content
        old_clip = ""
        try:
            old_clip = pyperclip.paste()
        except Exception:
            pass

        # Clear clipboard temporarily to detect fresh Ctrl+C copy
        try:
            pyperclip.copy("")
        except Exception:
            pass

        hwnd = win32gui.GetForegroundWindow()
        self._last_target_hwnd = hwnd

        # 2. Simulate Ctrl+C using keybd_event
        VK_CONTROL = 0x11
        KEYEVENTF_KEYUP = 0x0002
        ord_c = ord('C')

        win32api.keybd_event(VK_CONTROL, 0, 0, 0)
        win32api.keybd_event(ord_c, 0, 0, 0)
        time.sleep(0.04)
        win32api.keybd_event(ord_c, 0, KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)

        # 3. Poll clipboard for copied text
        t_end = time.time() + timeout
        selected = ""
        while time.time() < t_end:
            time.sleep(0.04)
            try:
                val = pyperclip.paste()
                if val and val.strip():
                    selected = val
                    break
            except Exception:
                pass

        if selected and selected.strip():
            self._last_original_text = selected
            return selected

        # Nothing was copied, restore old clipboard
        if old_clip:
            try:
                pyperclip.copy(old_clip)
            except Exception:
                pass
        return None

    def transform_text(
        self,
        text: str,
        transform_id: str,
        custom_instruction: Optional[str] = None
    ) -> TransformResult:
        """
        Applies deterministic transformation rules or optional local LLM.
        Returns a structured TransformResult guaranteeing truthful status reporting,
        original text preservation on failure, and enforced apply boundaries.
        """
        if not text or not text.strip():
            return TransformResult(
                original_text=text or "",
                candidate_text=text or "",
                status="unchanged",
                execution_route="none",
                guard_status="not_run",
                reason_code="EMPTY_INPUT",
                can_apply=False,
                error_message="Input text was empty."
            )

        raw = text.strip()
        candidate = raw
        route = "deterministic"

        if transform_id == "make_concise":
            candidate = self._apply_concise(raw)
        elif transform_id == "fix_grammar":
            candidate = self._apply_grammar_fix(raw)
        elif transform_id == "bullet_points":
            candidate = self._apply_bullet_points(raw)
        elif transform_id == "professional":
            candidate = self._apply_professional_tone(raw)
        elif transform_id == "casual":
            candidate = self._apply_casual_tone(raw)
        elif transform_id == "translate_en":
            # Text translation requires a capable local language model
            llm_ok = False
            try:
                from engine.local_llm import get_local_llm
                llm = get_local_llm()
                if llm.is_available():
                    out = llm.transform(raw, "Translate this text into clear, fluent English.")
                    if out and out.strip():
                        candidate = out.strip()
                        route = "local_llm"
                        llm_ok = True
            except Exception as e:
                logger.debug(f"[Transforms] Translation LLM error: {e}")

            if not llm_ok:
                with self._lock:
                    self._last_can_apply = False
                    self._last_execution_route = "none"
                return TransformResult(
                    original_text=text,
                    candidate_text=text,
                    status="unavailable",
                    execution_route="none",
                    guard_status="not_run",
                    reason_code="TRANSLATION_MODEL_UNAVAILABLE",
                    can_apply=False,
                    error_message="Text translation requires an optional local LLM. Your text was not changed."
                )

        elif transform_id == "custom":
            if not custom_instruction or not custom_instruction.strip():
                return TransformResult(
                    original_text=text,
                    candidate_text=text,
                    status="unchanged",
                    execution_route="none",
                    guard_status="not_run",
                    reason_code="EMPTY_INSTRUCTION",
                    can_apply=False,
                    error_message="Custom instruction was empty."
                )

            # 1. Try local offline LLM first for generative prompt execution
            llm_attempted = False
            try:
                from engine.local_llm import get_local_llm
                llm = get_local_llm()
                if llm.is_available():
                    llm_attempted = True
                    out = llm.transform(raw, custom_instruction)
                    if out and out.strip():
                        candidate = out.strip()
                        route = "local_llm"
                    else:
                        with self._lock:
                            self._last_can_apply = False
                            self._last_execution_route = "none"
                        return TransformResult(
                            original_text=text,
                            candidate_text=text,
                            status="unavailable",
                            execution_route="local_llm",
                            guard_status="not_run",
                            reason_code="LOCAL_LLM_EMPTY_OUTPUT",
                            can_apply=False,
                            error_message="Local LLM returned empty output. Your text was not changed."
                        )
            except Exception as e:
                logger.debug(f"[Transforms] Local LLM custom transform error: {e}")
                if llm_attempted:
                    with self._lock:
                        self._last_can_apply = False
                        self._last_execution_route = "none"
                    return TransformResult(
                        original_text=text,
                        candidate_text=text,
                        status="unavailable",
                        execution_route="local_llm",
                        guard_status="not_run",
                        reason_code="LOCAL_LLM_ERROR",
                        can_apply=False,
                        error_message=f"Local LLM failed ({e}). Your text was not changed."
                    )

            if not llm_attempted:
                # 2. Narrow anchored allowlist for deterministic presets
                inst = custom_instruction.strip()
                if RE_CUSTOM_BULLETS.match(inst):
                    candidate = self._apply_bullet_points(raw)
                    route = "deterministic"
                elif RE_CUSTOM_CONCISE.match(inst):
                    candidate = self._apply_concise(raw)
                    route = "deterministic"
                elif RE_CUSTOM_PROFESSIONAL.match(inst):
                    candidate = self._apply_professional_tone(raw)
                    route = "deterministic"
                elif RE_CUSTOM_CASUAL.match(inst):
                    candidate = self._apply_casual_tone(raw)
                    route = "deterministic"
                elif RE_CUSTOM_GRAMMAR.match(inst):
                    candidate = self._apply_grammar_fix(raw)
                    route = "deterministic"
                else:
                    # Unsupported natural language instruction without LLM (e.g. 'replace Friday with Monday')
                    # Must preserve exact original input text and report unsupported
                    with self._lock:
                        self._last_can_apply = False
                        self._last_execution_route = "none"
                    return TransformResult(
                        original_text=text,
                        candidate_text=text,
                        status="unsupported",
                        execution_route="none",
                        guard_status="not_run",
                        reason_code="LOCAL_LLM_REQUIRED",
                        can_apply=False,
                        error_message="This instruction needs the optional local writing model. Your text was not changed."
                    )
        else:
            # Unknown preset ID
            with self._lock:
                self._last_can_apply = False
                self._last_execution_route = "none"
            return TransformResult(
                original_text=text,
                candidate_text=text,
                status="unsupported",
                execution_route="none",
                guard_status="not_run",
                reason_code="UNKNOWN_PRESET",
                can_apply=False,
                error_message=f"Unknown transform preset '{transform_id}'. Your text was not changed."
            )

        # FactGuard invariant verification: Numbers, currencies, negations
        fg = FactGuard.verify_invariants(raw, candidate)
        factguard_passed = fg.get("passed", True)
        if not factguard_passed:
            with self._lock:
                self._last_can_apply = False
                self._last_execution_route = route
            return TransformResult(
                original_text=text,
                candidate_text=candidate,
                status="blocked",
                execution_route=route,
                guard_status="failed",
                reason_code="FACTGUARD_INVARIANT_VIOLATION",
                can_apply=False,
                error_message="Transform blocked: FactGuard invariant violation (numbers, dates, or negations altered)."
            )

        with self._lock:
            self._last_original_text = text
            self._last_transformed_text = candidate
            self._last_can_apply = True
            self._last_execution_route = route
            self._history.append({
                "timestamp": time.time(),
                "transform_id": transform_id,
                "original": text,
                "transformed": candidate,
                "factguard_passed": True,
                "route": route
            })

        return TransformResult(
            original_text=text,
            candidate_text=candidate,
            status="success",
            execution_route=route,
            guard_status="passed",
            reason_code="SUCCESS",
            can_apply=True
        )

    def replace_selection(
        self,
        replacement_text: str,
        target_hwnd: Optional[int] = None,
        result: Optional[TransformResult] = None,
        transaction: Optional[Any] = None
    ) -> InjectionResult:
        """
        Refuses external replacement until a real target adapter is implemented.

        Formatting eligibility and caller-supplied transaction labels do not prove
        document ownership. Scratchpad edits use VoiceEditor.apply_transaction()
        directly. The transaction argument is retained for caller compatibility,
        but cannot authorize input through this method.
        """
        if result is not None and not result.can_apply:
            logger.warning("[Transforms] Injection blocked: TransformResult has can_apply=False.")
            return InjectionResult(
                status=InjectionStatus.CANCELLED,
                error_message="Injection blocked: TransformResult has can_apply=False.",
                recovery_available=False
            )

        with self._lock:
            if result is None and not getattr(self, "_last_can_apply", False):
                logger.warning("[Transforms] Injection blocked: Last transform has can_apply=False.")
                return InjectionResult(
                    status=InjectionStatus.CANCELLED,
                    error_message="Injection blocked: last transform has can_apply=False.",
                    recovery_available=False
                )

        if not replacement_text:
            return InjectionResult(
                status=InjectionStatus.CANCELLED,
                error_message="Empty replacement text provided.",
                recovery_available=False
            )

        TextInjector.last_injected_text = replacement_text
        return InjectionResult(
            status=InjectionStatus.FAILED_RECOVERY_AVAILABLE,
            target_hwnd=target_hwnd or self._last_target_hwnd,
            error_message=(
                "External in-place replacement unavailable: document revision and "
                "selection cannot be verified. Use Copy Output and paste manually."
            ),
            recovery_available=True,
        )

    def revert_last_transform(
        self,
        target_hwnd: Optional[int] = None,
        transaction: Optional[Any] = None
    ) -> InjectionResult:
        """
        Refuses external revert without a verified record of the applied edit.

        Reinserting old text at the current cursor is not an undo. Scratchpad
        undo remains available through its separate VoiceEditor transactions.
        """
        with self._lock:
            orig = self._last_original_text
            hwnd = target_hwnd or self._last_target_hwnd

        if not orig:
            return InjectionResult(
                status=InjectionStatus.CANCELLED,
                error_message="No previous transform text found to revert.",
                recovery_available=False
            )

        TextInjector.last_injected_text = orig
        return InjectionResult(
            status=InjectionStatus.FAILED_RECOVERY_AVAILABLE,
            target_hwnd=hwnd,
            error_message=(
                "External revert unavailable: the prior edit and document revision "
                "cannot be verified. Original text remains in memory for recovery."
            ),
            recovery_available=True,
        )

    # -----------------------------------------------------------------
    # Deterministic Local Transformation Primitives
    # -----------------------------------------------------------------
    def _apply_concise(self, text: str) -> str:
        # Strip conversational padding and filler phrases
        filler_patterns = [
            r"\b(i mean|you know|sort of|kind of|basically|actually|literally|honestly)\b",
            r"\b(as a matter of fact|at the end of the day|in my humble opinion|needless to say)\b",
            r"\b(for all intents and purposes|in order to)\b",
            r"\b(it is important to note that|it should be pointed out that)\b",
            r"\b(just wanted to let you know that|i just wanted to follow up and see if)\b",
            r"\b(please let me know if you have any questions or concerns)\b"
        ]
        out = text
        for pat in filler_patterns:
            out = re.sub(pat, "", out, flags=re.IGNORECASE)

        # Clean multiple spaces and trim
        out = re.sub(r"[ \t]{2,}", " ", out)
        out = re.sub(r"\n{3,}", "\n\n", out)
        # Simplify "in order to" -> "to"
        out = re.sub(r"\bin order to\b", "to", out, flags=re.IGNORECASE)
        # Capitalize first letter of each sentence
        sentences = re.split(r"([.!?]\s+)", out.strip())
        capitalized = []
        for s in sentences:
            if s and s[0].isalpha():
                capitalized.append(s[0].upper() + s[1:])
            else:
                capitalized.append(s)
        return "".join(capitalized).strip()

    def _apply_grammar_fix(self, text: str) -> str:
        out = text.strip()
        # Common phonetic typo fixes
        replacements = [
            (r"\bteh\b", "the"),
            (r"\brecieve\b", "receive"),
            (r"\bseperate\b", "separate"),
            (r"\buntill\b", "until"),
            (r"\bdefinately\b", "definitely"),
            (r"\bi\b", "I"),
            (r"\bi'm\b", "I'm"),
            (r"\bi'll\b", "I'll"),
            (r"\bi've\b", "I've"),
            (r"\bdont\b", "don't"),
            (r"\bcant\b", "can't"),
            (r"\bwont\b", "won't"),
            (r"\bthats\b", "that's"),
            (r"\bits\b(?=\s+(?:a|an|the|my|your|very|so|too|really))", "it's"),
        ]
        for pat, rep in replacements:
            out = re.sub(pat, rep, out, flags=re.IGNORECASE)

        # Fix spacing around punctuation: "word ,word" -> "word, word"
        out = re.sub(r"\s+([,.:;?!])", r"\1", out)
        out = re.sub(r"([,.:;?!])([^\s0-9])", r"\1 \2", out)

        # Ensure terminal punctuation
        if out and out[-1] not in ".!?":
            out += "."
        # Capitalize start
        if out and out[0].islower():
            out = out[0].upper() + out[1:]
        return out

    def _apply_bullet_points(self, text: str) -> str:
        # Split on newlines, semicolons, or sentence terminators
        chunks = re.split(r"(?:\n+|;\s*|(?<=[.!?])\s+)", text.strip())
        bullets = []
        for c in chunks:
            clean = c.strip().lstrip("-*•>0123456789. ")
            if clean:
                if clean[0].islower():
                    clean = clean[0].upper() + clean[1:]
                bullets.append(f"- {clean}")
        return "\n".join(bullets) if bullets else f"- {text.strip()}"

    def _apply_professional_tone(self, text: str) -> str:
        out = self._apply_grammar_fix(text)
        phrases = [
            (r"\bgonna\b", "going to"),
            (r"\bwanna\b", "want to"),
            (r"\bgotta\b", "must"),
            (r"\byeah|yep|yup\b", "yes"),
            (r"\bnope\b", "no"),
            (r"\bhey\b", "Hello"),
            (r"\bthanks a bunch|thx\b", "Thank you"),
            (r"\bASAP\b", "as soon as possible"),
            (r"\bcatch you later|bye\b", "Best regards"),
            (r"\btalk soon\b", "Looking forward to speaking with you"),
            (r"\bi think we should\b", "I recommend that we"),
            (r"\bcan you please fix this\b", "Could you please address this issue"),
        ]
        for pat, rep in phrases:
            out = re.sub(pat, rep, out, flags=re.IGNORECASE)
        return out

    def _apply_casual_tone(self, text: str) -> str:
        out = text.strip()
        phrases = [
            (r"\bI am writing to inform you that\b", "Just wanted to let you know"),
            (r"\bPlease be advised that\b", "Quick heads up:"),
            (r"\bFurthermore|Moreover\b", "Also,"),
            (r"\bIn accordance with\b", "Following"),
            (r"\bDo not hesitate to contact me\b", "Feel free to reach out"),
            (r"\bSincerely|Regards|Best regards\b", "Cheers"),
            (r"\bKindly\b", "Please"),
        ]
        for pat, rep in phrases:
            out = re.sub(pat, rep, out, flags=re.IGNORECASE)
        return out

_transforms_instance: Optional[TransformsEngine] = None

def get_transforms_engine() -> TransformsEngine:
    global _transforms_instance
    if _transforms_instance is None:
        _transforms_instance = TransformsEngine()
    return _transforms_instance
