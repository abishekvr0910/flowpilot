"""
FlowPilot Universal Selection-Aware In-Place Text Rewriter (WP-2)
Authoritative implementation of verified in-place selection rewriting,
command intent classification, and atomic undo latch.

Safety Invariants:
1. Focus Safety: Never inject if the target window focus shifts during processing.
2. Terminal Protection: Never auto-replace or submit text into console/terminal windows.
3. Password Shield: Never read or overwrite password/credential fields.
4. FactGuard Invariant: Strictly preserves numbers, currency, dates, and negations.
5. Instant Undo: Every replacement registers an UndoTransaction for instant Alt+Shift+U revert.
"""

import re
import time
import uuid
import hashlib
import logging
import threading
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field

from engine.writing_intelligence import FactGuard
from engine.voice_editor import VoiceEditor, TERMINAL_PROCESSES, hash_text
from engine.transforms_engine import TransformsEngine, TransformResult
from engine.text_injector import TextInjector, InjectionResult, InjectionStatus

logger = logging.getLogger("FlowPilot.SelectionRewriter")

# Anchored regex patterns for spoken rewrite commands
RE_CMD_CONCISE = re.compile(
    r"^\s*(?:please\s+)?(?:make\s+(?:this|it)?\s*)?(?:concise|shorter|brief|summarize(?:\s+(?:this|it))?)\s*$",
    re.IGNORECASE
)
RE_CMD_PROFESSIONAL = re.compile(
    r"^\s*(?:please\s+)?(?:make\s+(?:this|it)?\s*)?(?:professional|formal|executive)(?:\s+tone)?\s*$",
    re.IGNORECASE
)
RE_CMD_CASUAL = re.compile(
    r"^\s*(?:please\s+)?(?:make\s+(?:this|it)?\s*)?(?:casual|friendly|relaxed)(?:\s+tone)?\s*$",
    re.IGNORECASE
)
RE_CMD_BULLETS = re.compile(
    r"^\s*(?:please\s+)?(?:format|convert|make|turn)?\s*(?:this|it)?\s*(?:in\s*to|as)?\s*(?:a\s+)?(?:bullet\s+points?|bulleted\s+list|bullet\s+list|bullets)\s*$",
    re.IGNORECASE
)
RE_CMD_GRAMMAR = re.compile(
    r"^\s*(?:please\s+)?(?:fix|correct|clean(?:\s+up)?)\s*(?:the\s+)?(?:grammar|typos?|spelling)\s*$",
    re.IGNORECASE
)
RE_CMD_TRANSLATE_EN = re.compile(
    r"^\s*(?:please\s+)?translate\s+(?:this\s+)?(?:in\s*to|to)\s+english\s*$",
    re.IGNORECASE
)
RE_CMD_UNDO = re.compile(
    r"^\s*(?:undo|revert)(?:\s+(?:that|last|the))?(?:\s+edit|\s+rewrite|\s+transform)?\s*$",
    re.IGNORECASE
)


@dataclass
class RewriteTransaction:
    transaction_id: str
    target_hwnd: int
    target_title: str
    process_name: str
    original_text: str
    candidate_text: str
    command_spoken: str
    intent: str
    applied: bool = False
    reverted: bool = False
    timestamp: float = field(default_factory=time.time)
    revision_hash: str = ""

    def __post_init__(self):
        if not self.revision_hash:
            self.revision_hash = hash_text(self.original_text)


@dataclass
class RewriteResult:
    status: str  # "applied" | "aborted_focus" | "blocked_safety" | "blocked_factguard" | "unsupported" | "error"
    original_text: str
    replacement_text: str
    intent: str
    transaction_id: Optional[str] = None
    error_message: Optional[str] = None
    can_undo: bool = False


class SelectionRewriter:
    """
    Universal selection-aware in-place text rewriter.
    Safely captures active selection, classifies voice intent, transforms
    text with deterministic FactGuard verification, and executes atomic replacement
    with an immediate Undo transaction.
    """

    def __init__(self, transforms_engine: Optional[TransformsEngine] = None):
        self.transforms_engine = transforms_engine or TransformsEngine()
        self._undo_stack: List[RewriteTransaction] = []
        self._max_undo_depth = 32
        self._lock = threading.RLock()

    @staticmethod
    def classify_intent(spoken_input: str) -> Tuple[str, Optional[str]]:
        """
        Classifies spoken user input into a transformation intent.
        Returns (intent, parameter_or_cleaned_instruction).
        """
        raw = spoken_input.strip()
        if not raw:
            return "empty", None

        if RE_CMD_UNDO.match(raw):
            return "undo", None
        if RE_CMD_CONCISE.match(raw):
            return "make_concise", None
        if RE_CMD_PROFESSIONAL.match(raw):
            return "professional", None
        if RE_CMD_CASUAL.match(raw):
            return "casual", None
        if RE_CMD_BULLETS.match(raw):
            return "bullet_points", None
        if RE_CMD_GRAMMAR.match(raw):
            return "fix_grammar", None
        if RE_CMD_TRANSLATE_EN.match(raw):
            return "translate_en", None

        # Check for natural imperative instructions: "replace X with Y", "change X to Y"
        if re.match(r"^\s*(?:replace|change)\s+.+\s+(?:with|to)\s+.+$", raw, re.IGNORECASE):
            return "custom_instruction", raw
        if re.match(r"^\s*(?:translate|convert|rewrite|rephrase)\s+", raw, re.IGNORECASE):
            return "custom_instruction", raw

        # Default: user is dictating replacement text directly
        return "direct_replacement", raw

    def capture_selection(self, timeout: float = 0.35) -> Tuple[Optional[str], int, str, str]:
        """
        Captures the currently selected text from the active foreground window.
        Returns (selected_text, hwnd, title, process_name).
        """
        hwnd, title, proc_name = TextInjector.get_target_window_info()
        getter = getattr(self.transforms_engine, "get_selected_text_from_active_window", None) or getattr(self.transforms_engine, "extract_selected_text", None)
        selected_text = getter(timeout=timeout) if callable(getter) else None
        return selected_text, hwnd, title, proc_name

    def process_and_rewrite(
        self,
        spoken_command: str,
        selected_text: Optional[str] = None,
        target_hwnd: Optional[int] = None
    ) -> RewriteResult:
        """
        End-to-end execution of a selection rewrite:
        1. Capture selection if not supplied
        2. Validate target safety (no terminals, no password fields)
        3. Classify command intent (concise, professional, bullets, or direct replacement)
        4. Execute transform with FactGuard invariant check
        5. Verify active window focus has not shifted
        6. Inject replacement text into selection
        7. Register UndoTransaction
        """
        # 1. Capture selection if not pre-captured
        if selected_text is None or target_hwnd is None:
            captured, hwnd, title, proc_name = self.capture_selection()
            if not captured or not captured.strip():
                return RewriteResult(
                    status="unsupported",
                    original_text="",
                    replacement_text="",
                    intent="none",
                    error_message="No text was selected in the active window."
                )
            selected_text = captured
            target_hwnd = hwnd
        else:
            hwnd, title, proc_name = TextInjector.get_target_window_info()

        # 2. Validate target safety
        is_safe, safety_err = VoiceEditor.check_target_safety(proc_name, title)
        if not is_safe:
            logger.warning(f"[SelectionRewriter] Safety check blocked rewrite: {safety_err}")
            return RewriteResult(
                status="blocked_safety",
                original_text=selected_text,
                replacement_text="",
                intent="none",
                error_message=safety_err
            )

        # 3. Classify intent
        intent, param = self.classify_intent(spoken_command)

        # Handle spoken "undo" command
        if intent == "undo":
            undone = self.undo_last_rewrite(expected_hwnd=target_hwnd)
            if undone:
                return RewriteResult(
                    status="applied",
                    original_text="",
                    replacement_text="",
                    intent="undo",
                    can_undo=False
                )
            else:
                return RewriteResult(
                    status="error",
                    original_text="",
                    replacement_text="",
                    intent="undo",
                    error_message="Nothing to undo or active window changed."
                )

        # 4. Generate candidate replacement text
        candidate_text = selected_text
        if intent == "direct_replacement":
            candidate_text = param or spoken_command
        elif intent in ("make_concise", "professional", "casual", "bullet_points", "fix_grammar", "translate_en"):
            res = self.transforms_engine.transform_text(selected_text, intent)
            if not res.can_apply or res.status != "success":
                return RewriteResult(
                    status="blocked_factguard" if res.guard_status == "failed" else "unsupported",
                    original_text=selected_text,
                    replacement_text=selected_text,
                    intent=intent,
                    error_message=res.error_message
                )
            candidate_text = res.candidate_text
        elif intent == "custom_instruction":
            res = self.transforms_engine.transform_text(selected_text, "custom", custom_instruction=param)
            if not res.can_apply or res.status != "success":
                return RewriteResult(
                    status="blocked_factguard" if res.guard_status == "failed" else "unsupported",
                    original_text=selected_text,
                    replacement_text=selected_text,
                    intent=intent,
                    error_message=res.error_message
                )
            candidate_text = res.candidate_text
        else:
            return RewriteResult(
                status="unsupported",
                original_text=selected_text,
                replacement_text=selected_text,
                intent=intent,
                error_message=f"Unsupported rewrite intent: {intent}"
            )

        # 5. Deterministic FactGuard Invariant Check
        if intent != "direct_replacement":
            fg = FactGuard.verify_invariants(selected_text, candidate_text)
            if not fg.get("passed", True):
                logger.warning("[SelectionRewriter] FactGuard invariant check failed; blocking rewrite.")
                return RewriteResult(
                    status="blocked_factguard",
                    original_text=selected_text,
                    replacement_text=candidate_text,
                    intent=intent,
                    error_message="FactGuard invariant violation: numbers, currency, dates, or negations altered."
                )

        # 6. Focus-Shift Abort Safety Check immediately before injection
        cur_hwnd, cur_title, _ = TextInjector.get_target_window_info()
        if cur_hwnd != target_hwnd:
            logger.warning(f"[SelectionRewriter] Aborting: target focus shifted from {target_hwnd} to {cur_hwnd}.")
            # Store in recovery buffer so text is never lost
            TextInjector.last_injected_text = candidate_text
            return RewriteResult(
                status="aborted_focus",
                original_text=selected_text,
                replacement_text=candidate_text,
                intent=intent,
                error_message="Target window focus changed while speaking. Replacement staged to recovery buffer."
            )

        # 7. Execute in-place replacement via TextInjector
        # Since the selection is already highlighted, injecting candidate_text replaces the selection
        inj_res = TextInjector.inject_with_status(
            candidate_text,
            target_hwnd=target_hwnd,
            preceding_text="",
            following_text=""
        )

        if inj_res.status not in (InjectionStatus.CONFIRMED_INSERTED, InjectionStatus.SENT_UNVERIFIED):
            return RewriteResult(
                status="error",
                original_text=selected_text,
                replacement_text=candidate_text,
                intent=intent,
                error_message=f"Text injection failed: {inj_res.error_message}"
            )

        # 8. Register Undo Transaction
        tx = RewriteTransaction(
            transaction_id=f"tx_{uuid.uuid4().hex[:12]}",
            target_hwnd=target_hwnd,
            target_title=title,
            process_name=proc_name,
            original_text=selected_text,
            candidate_text=candidate_text,
            command_spoken=spoken_command,
            intent=intent,
            applied=True
        )

        with self._lock:
            self._undo_stack.append(tx)
            while len(self._undo_stack) > self._max_undo_depth:
                self._undo_stack.pop(0)

        logger.info(f"[SelectionRewriter] Applied rewrite '{intent}' ({len(selected_text)} -> {len(candidate_text)} chars). TxID={tx.transaction_id}")
        return RewriteResult(
            status="applied",
            original_text=selected_text,
            replacement_text=candidate_text,
            intent=intent,
            transaction_id=tx.transaction_id,
            can_undo=True
        )

    def undo_last_rewrite(self, expected_hwnd: Optional[int] = None) -> bool:
        """
        Rolls back the most recent rewrite transaction by replacing the
        candidate text with the original text.
        """
        with self._lock:
            if not self._undo_stack:
                logger.info("[SelectionRewriter] Undo stack is empty.")
                return False
            tx = self._undo_stack.pop()

        # Check target focus
        cur_hwnd, _, _ = TextInjector.get_target_window_info()
        target = expected_hwnd or tx.target_hwnd
        if cur_hwnd != target:
            logger.warning(f"[SelectionRewriter] Cannot undo: focus shifted ({cur_hwnd} != {target}).")
            # Push back onto stack
            with self._lock:
                self._undo_stack.append(tx)
            return False

        # Dispatch original text to restore
        inj_res = TextInjector.inject_with_status(tx.original_text, target_hwnd=target)
        success = inj_res.status in (InjectionStatus.CONFIRMED_INSERTED, InjectionStatus.SENT_UNVERIFIED)
        if success:
            tx.reverted = True
            logger.info(f"[SelectionRewriter] Successfully reverted transaction {tx.transaction_id}.")
        return success

    def clear_undo_history(self):
        with self._lock:
            self._undo_stack.clear()
