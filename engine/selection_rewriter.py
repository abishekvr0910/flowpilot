"""
External selection rewrite compatibility boundary.
Intent classification remains available, but capture, replacement, and undo refuse
external operations until a document revision and selection adapter exists.
"""

import re
import time
import logging
import threading
from typing import Optional, List, Tuple
from dataclasses import dataclass, field

from engine.voice_editor import hash_text
from engine.transforms_engine import TransformsEngine

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
    Intent classifier with disabled external mutation entry points.
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
        """External rewrite capture is disabled until a revision adapter exists."""
        return None, 0, "", ""

    def process_and_rewrite(
        self,
        spoken_command: str,
        selected_text: Optional[str] = None,
        target_hwnd: Optional[int] = None,
    ) -> RewriteResult:
        """Refuse external mutation, including caller-supplied selection labels."""
        intent, _ = self.classify_intent(spoken_command)
        return RewriteResult(
            status="unsupported",
            original_text=selected_text or "",
            replacement_text="",
            intent=intent,
            error_message=(
                "External selection rewriting is unavailable until document revision "
                "and selection verification exists. Use preview and Copy Output."
            ),
            can_undo=False,
        )

    def undo_last_rewrite(self, expected_hwnd: Optional[int] = None) -> bool:
        """Never paste an old selection at an unverified cursor position."""
        return False

    def clear_undo_history(self):
        with self._lock:
            self._undo_stack.clear()
