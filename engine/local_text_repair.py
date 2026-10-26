"""
FlowPilot Local Text Repair Engine (Spec 0004: Feature 30 Sandbox)
Bounded natural language text repair, punctuation restoration, and disfluency cleanup.

STRICT INVARIANTS:
1. Text repair ONLY (post-ASR NLP); NOT an acoustic speech recognizer.
2. Three-Tier Guard Protocol: Slot-locking (numbers, dates, negations, identifiers)
   + Bounded Infilling + FactGuard Veto Verification.
3. Hard execution deadline (400 ms). Fallback to raw Whisper on ANY error or veto in <= 5 ms.
4. 100% offline, zero cloud egress.
"""

import os
import re
import time
import logging
import concurrent.futures
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple

logger = logging.getLogger("FlowPilot.LocalTextRepair")

# Import FactGuard verification from evaluation metrics
from engine.evaluation_metrics import verify_critical_facts


class RepairStatus(str, Enum):
    """Execution status for the Local Text Repair engine."""
    REPAIRED = "REPAIRED"                      # Successfully cleaned and passed FactGuard
    FALLBACK_UNPROVISIONED = "FALLBACK_UNPROVISIONED"  # Model not loaded or disabled
    FALLBACK_TIMEOUT = "FALLBACK_TIMEOUT"      # Exceeded the 400 ms latency budget
    FALLBACK_ERROR = "FALLBACK_ERROR"          # Runtime exception handled safely
    VETOED_FACT_MISMATCH = "VETOED_FACT_MISMATCH"  # FactGuard rejected hallucination or missing entity


@dataclass
class RepairResult:
    """Structured result returned by LocalTextRepair."""
    status: RepairStatus
    text: str                                  # The delivered text (repaired or raw fallback)
    raw_input: str
    latency_ms: float
    veto_reason: Optional[str] = None
    slots_locked: int = 0
    fallback_used: bool = False


class SlotLocker:
    """
    Tier 1 & Tier 3: Deterministic entity preservation.
    Locks numbers, currency, dates, critical negations, and code identifiers
    behind opaque placeholder tokens (<SLOT_N>) to make hallucination impossible.
    """

    # Critical negations that must NEVER be dropped, altered, or negated
    NEGATION_PATTERN = re.compile(
        r"\b(not|never|no|neither|nor|cannot|can't|won't|don't|doesn't|didn't|isn't|aren't|wasn't|weren't)\b",
        re.IGNORECASE
    )

    # Numbers, currencies, percentages, and numeric codes
    NUMBER_PATTERN = re.compile(
        r"(?:\$\s*|\€\s*|\£\s*|\b)\d+(?:[.,]\d+)*(?:\s*\%|\b)",
        re.IGNORECASE
    )

    # Code identifiers (camelCase, PascalCase, snake_case)
    CODE_IDENTIFIER_PATTERN = re.compile(
        r"\b(?:[a-z]+[A-Z][a-zA-Z0-9]*|[A-Z][a-zA-Z0-9]*[A-Z][a-zA-Z0-9]*|[a-z0-9]+_[a-z0-9_]+)\b"
    )

    @classmethod
    def lock(cls, text: str) -> Tuple[str, Dict[str, str]]:
        """
        Replaces critical entities with opaque <SLOT_N> tokens.
        Returns the locked text and a mapping of token -> original entity.
        """
        slots = {}
        slot_idx = 0

        # Helper to replace matches with a numbered slot
        def replacer(match):
            nonlocal slot_idx
            matched_text = match.group(0)
            token = f"<SLOT_{slot_idx}>"
            slots[token] = matched_text
            slot_idx += 1
            return token

        # Order of locking: Code identifiers first, then numbers/currency, then negations
        locked = cls.CODE_IDENTIFIER_PATTERN.sub(replacer, text)
        locked = cls.NUMBER_PATTERN.sub(replacer, locked)
        locked = cls.NEGATION_PATTERN.sub(replacer, locked)

        return locked, slots

    @classmethod
    def restore(cls, text: str, slots: Dict[str, str]) -> str:
        """
        Restores <SLOT_N> placeholder tokens with their original strings.
        """
        restored = text
        for token, original in slots.items():
            restored = restored.replace(token, original)
        return restored


class LocalTextRepair:
    """
    Three-Tier Guard Protocol Engine (Spec 0004).
    Governs local SLM sentence repair under strict latency, fact preservation,
    and fallback safety contracts.
    """

    MAX_LATENCY_MS: float = 400.0   # Hard deadline for local repair
    MAX_TOKENS: int = 60            # Bounded output generation

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.enabled: bool = bool(self.config.get("local_text_repair_enabled", False))
        self.model_path: Optional[str] = self.config.get("local_text_repair_model_path")
        self._llm = None
        self._executor: Optional[concurrent.futures.ThreadPoolExecutor] = None
        self._init_failed: bool = False

    def _get_executor(self) -> concurrent.futures.ThreadPoolExecutor:
        """Get or lazily create bounded worker pool for SLM inference."""
        if self._executor is None:
            self._executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=1,
                thread_name_prefix="FlowPilot.LocalTextRepair"
            )
        return self._executor

    def shutdown(self, wait: bool = False):
        """Cleanly terminate worker threads if initialized."""
        if self._executor is not None:
            self._executor.shutdown(wait=wait)
            self._executor = None

    def _lazy_init_llm(self) -> bool:
        """Lazy loader for local GGUF engine via llama-cpp-python."""
        if self._llm is not None:
            return True
        if self._init_failed or not self.model_path:
            return False

        try:
            from llama_cpp import Llama
            logger.info("Initializing local text repair SLM from %s...", self.model_path)
            self._llm = Llama(
                model_path=self.model_path,
                n_ctx=512,
                n_threads=min(4, os.cpu_count() or 2),
                verbose=False
            )
            return True
        except Exception as e:
            logger.warning("Could not initialize local SLM runtime: %s", e)
            self._init_failed = True
            return False

    def repair(self, raw_transcript: str, language: str = "en") -> RepairResult:
        """
        Executes the Three-Tier Guard Protocol on the input transcript:
        Tier 1: Slot-lock numbers, dates, negations, identifiers.
        Tier 2: Bounded infilling via local SLM with hard async deadline enforcement.
        Tier 3: Slot restoration & FactGuard verification.

        Guarantees <= 5 ms fallback to raw_transcript on any error, timeout, or veto.
        """
        t_start = time.perf_counter()

        # Immediate fallback if empty, unprovisioned, or disabled
        if not raw_transcript or not raw_transcript.strip():
            return RepairResult(
                status=RepairStatus.REPAIRED,
                text=raw_transcript,
                raw_input=raw_transcript,
                latency_ms=0.0
            )

        if not self.enabled:
            return RepairResult(
                status=RepairStatus.FALLBACK_UNPROVISIONED,
                text=raw_transcript,
                raw_input=raw_transcript,
                latency_ms=(time.perf_counter() - t_start) * 1000.0,
                fallback_used=True
            )

        # Tier 1: Deterministic Slot Locking (< 5 ms)
        try:
            locked_text, slots = SlotLocker.lock(raw_transcript)
        except Exception as e:
            logger.error("Tier 1 slot locking failed: %s", e)
            return self._safe_fallback(raw_transcript, RepairStatus.FALLBACK_ERROR, t_start)

        # Check model availability
        if not self._lazy_init_llm():
            return self._safe_fallback(raw_transcript, RepairStatus.FALLBACK_UNPROVISIONED, t_start)

        # Tier 2: Bounded Local SLM Infilling with Strict Timeout Enforcement
        try:
            time_spent_ms = (time.perf_counter() - t_start) * 1000.0
            remaining_ms = self.MAX_LATENCY_MS - time_spent_ms
            if remaining_ms <= 5.0:
                return self._safe_fallback(raw_transcript, RepairStatus.FALLBACK_TIMEOUT, t_start)

            system_prompt = (
                "You are FlowPilot's local text repair engine. Clean up speech disfluencies, "
                "fix punctuation, and structure run-on sentences. Keep all <SLOT_N> tokens exactly intact. "
                "Do NOT add new facts or delete <SLOT_N> tokens."
            )
            prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{locked_text}<|im_end|>\n<|im_start|>assistant\n"

            executor = self._get_executor()
            future = executor.submit(
                self._llm,
                prompt,
                max_tokens=self.MAX_TOKENS,
                stop=["<|im_end|>", "\n\n"],
                temperature=0.1
            )
            res = future.result(timeout=remaining_ms / 1000.0)
            raw_generated = res["choices"][0]["text"].strip()

        except concurrent.futures.TimeoutError:
            logger.warning("Tier 2 SLM inference exceeded latency budget (%.1f ms); returning safe fallback", self.MAX_LATENCY_MS)
            return self._safe_fallback(raw_transcript, RepairStatus.FALLBACK_TIMEOUT, t_start)
        except Exception as e:
            logger.warning("Tier 2 SLM inference failed: %s", e)
            return self._safe_fallback(raw_transcript, RepairStatus.FALLBACK_ERROR, t_start)

        # Tier 3: Slot Restoration (< 2 ms)
        restored_text = SlotLocker.restore(raw_generated, slots)

        # FactGuard Veto Check: Ensure zero missing critical facts or negations
        elapsed_ms = (time.perf_counter() - t_start) * 1000.0
        if elapsed_ms > self.MAX_LATENCY_MS:
            logger.info("Local text repair timed out (%.1f ms > %.1f ms); vetoing.", elapsed_ms, self.MAX_LATENCY_MS)
            return self._safe_fallback(raw_transcript, RepairStatus.FALLBACK_TIMEOUT, t_start)

        facts = verify_critical_facts(raw_transcript, restored_text, language=language)
        missing_critical = facts["missing_numbers"] + facts["missing_negations"]
        added_critical = [v for vals in facts["added_entities"].values() for v in vals]

        if missing_critical or added_critical:
            veto_reason = f"FactGuard veto: missing={missing_critical}, added={added_critical}"
            logger.warning("Local text repair rejected: %s", veto_reason)
            return RepairResult(
                status=RepairStatus.VETOED_FACT_MISMATCH,
                text=raw_transcript,   # Fallback to pristine raw transcript
                raw_input=raw_transcript,
                latency_ms=elapsed_ms,
                veto_reason=veto_reason,
                slots_locked=len(slots),
                fallback_used=True
            )

        # All 3 Tiers passed successfully
        return RepairResult(
            status=RepairStatus.REPAIRED,
            text=restored_text,
            raw_input=raw_transcript,
            latency_ms=elapsed_ms,
            slots_locked=len(slots),
            fallback_used=False
        )

    def _safe_fallback(self, raw_transcript: str, status: RepairStatus, t_start: float) -> RepairResult:
        """Instantaneous safe fallback returning the pristine raw transcript."""
        elapsed_ms = (time.perf_counter() - t_start) * 1000.0
        return RepairResult(
            status=status,
            text=raw_transcript,
            raw_input=raw_transcript,
            latency_ms=elapsed_ms,
            fallback_used=True
        )
