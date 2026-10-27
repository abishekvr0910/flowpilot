"""
FlowPilot Local Text Repair Engine (Spec 0004: Feature 30 Sandbox)
Bounded natural language text repair, punctuation restoration, and disfluency cleanup.

STRICT INVARIANTS:
1. Text repair ONLY (post-ASR NLP); NOT an acoustic speech recognizer.
2. Three-Tier Guard Protocol: Slot-locking (numbers, dates, negations, identifiers)
   + Bounded Infilling + FactGuard Veto Verification.
3. Hard execution deadline (400 ms). Fallback to raw Whisper on ANY error or veto in <= 5 ms.
4. Process Isolation: SLM runs in an isolated worker process that can be forcibly
   terminated (SIGTERM/kill) if native C++ inference hangs, eliminating thread leakage.
5. Asynchronous Non-Blocking Warmup: Model preloading executes asynchronously without
   stalling application startup or real-time dictation.
6. 100% offline, zero cloud egress.
"""

import os
import re
import time
import logging
import concurrent.futures
import multiprocessing as mp
from multiprocessing.connection import Connection
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

    NEGATION_PATTERN = re.compile(
        r"\b(not|never|no|neither|nor|cannot|can't|won't|don't|doesn't|didn't|isn't|aren't|wasn't|weren't)\b",
        re.IGNORECASE
    )

    NUMBER_PATTERN = re.compile(
        r"(?:\$\s*|\€\s*|\£\s*|\b)\d+(?:[.,]\d+)*(?:\s*\%|\b)",
        re.IGNORECASE
    )

    CODE_IDENTIFIER_PATTERN = re.compile(
        r"\b(?:[a-z]+[A-Z][a-zA-Z0-9]*|[A-Z][a-zA-Z0-9]*[A-Z][a-zA-Z0-9]*|[a-z0-9]+_[a-z0-9_]+)\b"
    )

    @classmethod
    def lock(cls, text: str) -> Tuple[str, Dict[str, str]]:
        slots = {}
        slot_idx = 0

        def replacer(match):
            nonlocal slot_idx
            matched_text = match.group(0)
            token = f"<SLOT_{slot_idx}>"
            slots[token] = matched_text
            slot_idx += 1
            return token

        locked = cls.CODE_IDENTIFIER_PATTERN.sub(replacer, text)
        locked = cls.NUMBER_PATTERN.sub(replacer, locked)
        locked = cls.NEGATION_PATTERN.sub(replacer, locked)

        return locked, slots

    @classmethod
    def restore(cls, text: str, slots: Dict[str, str]) -> str:
        restored = text
        for token, original in slots.items():
            restored = restored.replace(token, original)
        return restored

    @classmethod
    def find_missing_slots(cls, generated_text: str, slots: Dict[str, str]) -> List[str]:
        """Returns original values of any locked <SLOT_N> tokens dropped by the SLM."""
        return [original for token, original in slots.items() if token not in generated_text]

    @classmethod
    def find_duplicated_slots(cls, generated_text: str, slots: Dict[str, str]) -> List[str]:
        """Returns original values of any locked <SLOT_N> tokens duplicated by the SLM."""
        return [original for token, original in slots.items() if generated_text.count(token) > 1]


DEFAULT_SYSTEM_PROMPT = (
    "You are FlowPilot's local text repair engine. Clean up speech disfluencies (um, uh), "
    "fix capitalization and punctuation, and keep every <SLOT_N> token in its exact position. "
    "Do NOT add new facts, explanations, or delete any <SLOT_N> token.\n"
    "Example:\n"
    "User: um we must <SLOT_2> deploy commit <SLOT_0> before <SLOT_1> pm in <SLOT_3>\n"
    "Assistant: We must <SLOT_2> deploy commit <SLOT_0> before <SLOT_1> pm in <SLOT_3>."
)


def _slm_process_worker_entry(pipe: Connection, model_path: Optional[str], n_threads: int):
    """
    Independent worker process entry point for local SLM inference.
    Runs in a dedicated OS process to allow hard termination if native C++ inference hangs.
    """
    llm = None
    try:
        if model_path:
            from llama_cpp import Llama
            llm = Llama(
                model_path=model_path,
                n_ctx=512,
                n_batch=256,
                n_threads=n_threads,
                verbose=False
            )
            warmup_prompt = (
                f"<|im_start|>system\n{DEFAULT_SYSTEM_PROMPT}<|im_end|>\n"
                "<|im_start|>user\nwarmup<|im_end|>\n<|im_start|>assistant\n"
            )
            llm(warmup_prompt, max_tokens=1, stop=["<|im_end|>", "\n"], temperature=0.0)
            pipe.send({"status": "ready"})
        else:
            pipe.send({"status": "error", "error": "No model path provided"})
    except Exception as e:
        try:
            pipe.send({"status": "error", "error": str(e)})
        except Exception:
            pass

    # Worker command loop
    while True:
        try:
            if not pipe.poll(timeout=0.5):
                continue
            req = pipe.recv()
            if not isinstance(req, dict):
                continue

            cmd = req.get("cmd")
            if cmd == "shutdown":
                break
            elif cmd == "ping":
                pipe.send({"status": "pong"})
            elif cmd == "infer":
                prompt = req.get("prompt")
                max_tokens = req.get("max_tokens", 60)
                stop = req.get("stop", ["<|im_end|>", "\n"])
                temperature = req.get("temperature", 0.0)

                if llm is None:
                    pipe.send({"status": "error", "error": "Model not initialized"})
                    continue

                res = llm(
                    prompt,
                    max_tokens=max_tokens,
                    stop=stop,
                    temperature=temperature
                )
                text = res["choices"][0]["text"].strip()
                pipe.send({"status": "ok", "text": text})

        except (EOFError, BrokenPipeError):
            break
        except Exception as e:
            try:
                pipe.send({"status": "error", "error": str(e)})
            except Exception:
                break


class LocalTextRepair:
    """
    Three-Tier Guard Protocol Engine (Spec 0004).
    Governs local SLM sentence repair under strict latency, fact preservation,
    and process-isolated fallback safety contracts.
    """

    MAX_LATENCY_MS: float = 400.0   # Hard deadline for local repair
    MAX_TOKENS: int = 60            # Bounded output generation

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.enabled: bool = bool(self.config.get("local_text_repair_enabled", False))
        self.model_path: Optional[str] = self.config.get("local_text_repair_model_path")
        self.worker_mode: str = self.config.get("local_text_repair_worker_mode", "process")
        
        # In-process mock / fallback callable (used for unit tests and thread mode)
        self._llm = None
        self._executor: Optional[concurrent.futures.ThreadPoolExecutor] = None
        
        # Process worker state
        self._worker_process: Optional[mp.Process] = None
        self._parent_pipe: Optional[Connection] = None
        self._is_ready: bool = False
        self._init_failed: bool = False
        
        # Asynchronous warmup state
        self._warmup_future: Optional[concurrent.futures.Future] = None
        self._warmup_in_progress: bool = False

    def _get_executor(self) -> concurrent.futures.ThreadPoolExecutor:
        """Get or lazily create bounded worker pool for in-process LLM inference."""
        if self._executor is None:
            self._executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=2,
                thread_name_prefix="FlowPilot.LocalTextRepair"
            )
        return self._executor

    def _ensure_worker_process(self, timeout_sec: float = 3.0) -> bool:
        """Spawns and initializes dedicated worker process if not already running."""
        if self._worker_process is not None and self._worker_process.is_alive():
            if self._is_ready:
                return True
            # Worker process is starting; check for ready signal up to timeout_sec
            if self._parent_pipe is not None and self._parent_pipe.poll(timeout=timeout_sec):
                msg = self._parent_pipe.recv()
                if msg.get("status") == "ready":
                    self._is_ready = True
                    return True
                else:
                    logger.warning("Worker process reported init error: %s", msg.get("error"))
                    self._terminate_worker_process()
                    self._init_failed = True
                    return False
            return False

        if self._init_failed or not self.model_path:
            return False

        try:
            ctx = mp.get_context("spawn")
            parent_conn, child_conn = ctx.Pipe(duplex=True)
            n_threads = min(4, os.cpu_count() or 2)
            
            p = ctx.Process(
                target=_slm_process_worker_entry,
                args=(child_conn, self.model_path, n_threads),
                daemon=True
            )
            p.start()
            self._worker_process = p
            self._parent_pipe = parent_conn
            self._is_ready = False

            # Bounded wait for ready signal
            if parent_conn.poll(timeout=timeout_sec):
                msg = parent_conn.recv()
                if msg.get("status") == "ready":
                    self._is_ready = True
                    return True
                else:
                    logger.warning("Worker process reported init error: %s", msg.get("error"))
                    self._terminate_worker_process()
                    self._init_failed = True
                    return False
            else:
                logger.warning("Worker process startup timed out after %.2f s.", timeout_sec)
                # If timeout was long (>=2s), mark as failed; if short (cold start check), leave running
                if timeout_sec >= 2.0:
                    self._terminate_worker_process()
                    self._init_failed = True
                return False

        except Exception as e:
            logger.warning("Could not launch SLM worker process: %s", e)
            self._terminate_worker_process()
            self._init_failed = True
            return False

    def _terminate_worker_process(self):
        """Hard-terminates the worker process and frees all OS handles."""
        self._is_ready = False
        if self._worker_process is not None:
            try:
                if self._worker_process.is_alive():
                    self._worker_process.terminate()
                    self._worker_process.join(timeout=0.2)
                    if self._worker_process.is_alive():
                        self._worker_process.kill()
            except Exception as e:
                logger.debug("Error terminating worker process: %s", e)
            self._worker_process = None

        if self._parent_pipe is not None:
            try:
                self._parent_pipe.close()
            except Exception:
                pass
            self._parent_pipe = None

    def warmup(self) -> bool:
        """Synchronously pre-loads model weights in the worker process."""
        if self._llm is not None:
            return True
        return self._ensure_worker_process(timeout_sec=3.0)

    def warmup_async(self) -> concurrent.futures.Future:
        """
        Initiates asynchronous worker spawn and model pre-loading on a background thread.
        Does not block application startup or the GUI event loop.
        """
        if self._warmup_future is not None and not self._warmup_future.done():
            return self._warmup_future

        executor = self._get_executor()
        self._warmup_in_progress = True

        def _task():
            try:
                ready = self.warmup()
                self._is_ready = bool(ready)
                return ready
            finally:
                self._warmup_in_progress = False

        self._warmup_future = executor.submit(_task)
        return self._warmup_future

    def shutdown(self, wait: bool = False):
        """Cleanly terminate worker process and executor."""
        if self._parent_pipe is not None and self._worker_process is not None and self._worker_process.is_alive():
            try:
                self._parent_pipe.send({"cmd": "shutdown"})
                self._worker_process.join(timeout=0.2)
            except Exception:
                pass
        self._terminate_worker_process()

        if self._executor is not None:
            self._executor.shutdown(wait=wait)
            self._executor = None

    def _infer_bounded(self, prompt: str, remaining_ms: float) -> str:
        """
        Executes inference within remaining_ms.
        If self._llm is set (mock/thread mode), runs via ThreadPoolExecutor.
        Otherwise, runs via isolated worker process with hard process termination on timeout.
        """
        remaining_sec = remaining_ms / 1000.0

        # Mode A: In-process callable (used for unit tests and mock overrides)
        if self._llm is not None:
            executor = self._get_executor()
            future = executor.submit(
                self._llm,
                prompt,
                max_tokens=self.MAX_TOKENS,
                stop=["<|im_end|>", "\n"],
                temperature=0.0
            )
            res = future.result(timeout=remaining_sec)
            return res["choices"][0]["text"].strip()

        # Mode B: Process-isolated worker (production baseline)
        if not self._ensure_worker_process(timeout_sec=min(0.2, remaining_sec)):
            raise RuntimeError("SLM worker process unavailable")

        self._parent_pipe.send({
            "cmd": "infer",
            "prompt": prompt,
            "max_tokens": self.MAX_TOKENS,
            "stop": ["<|im_end|>", "\n"],
            "temperature": 0.0
        })

        if not self._parent_pipe.poll(timeout=remaining_sec):
            logger.warning("SLM inference exceeded deadline (%.1f ms); terminating worker process...", self.MAX_LATENCY_MS)
            self._terminate_worker_process()
            raise concurrent.futures.TimeoutError("Worker process inference timed out")

        resp = self._parent_pipe.recv()
        if resp.get("status") == "ok":
            return resp["text"]
        else:
            raise RuntimeError(resp.get("error", "Unknown worker inference error"))

    def repair(self, raw_transcript: str, language: str = "en") -> RepairResult:
        """
        Executes the Three-Tier Guard Protocol on the input transcript:
        Tier 1: Slot-lock numbers, dates, negations, identifiers.
        Tier 2: Bounded infilling via local SLM with hard process-isolated deadline enforcement.
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
        if self._llm is None:
            if not self.model_path:
                return self._safe_fallback(raw_transcript, RepairStatus.FALLBACK_UNPROVISIONED, t_start)

            time_spent_ms = (time.perf_counter() - t_start) * 1000.0
            remaining_ms = self.MAX_LATENCY_MS - time_spent_ms
            if remaining_ms <= 5.0:
                return self._safe_fallback(raw_transcript, RepairStatus.FALLBACK_TIMEOUT, t_start)

            # Cold-start safety: bounded check (at most 50 ms if cold)
            cold_check_sec = min(0.05, remaining_ms / 1000.0)
            if not self._ensure_worker_process(timeout_sec=cold_check_sec):
                # Return raw fallback immediately without waiting for cold start
                return self._safe_fallback(raw_transcript, RepairStatus.FALLBACK_UNPROVISIONED, t_start)

        # Tier 2: Bounded Local SLM Infilling with Process-Isolated Hard Timeout
        try:
            time_spent_ms = (time.perf_counter() - t_start) * 1000.0
            remaining_ms = self.MAX_LATENCY_MS - time_spent_ms
            if remaining_ms <= 5.0:
                return self._safe_fallback(raw_transcript, RepairStatus.FALLBACK_TIMEOUT, t_start)

            system_prompt = DEFAULT_SYSTEM_PROMPT
            prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{locked_text}<|im_end|>\n<|im_start|>assistant\n"

            raw_generated = self._infer_bounded(prompt, remaining_ms)

        except concurrent.futures.TimeoutError:
            logger.warning("Tier 2 SLM inference exceeded latency budget (%.1f ms); returning safe fallback", self.MAX_LATENCY_MS)
            return self._safe_fallback(raw_transcript, RepairStatus.FALLBACK_TIMEOUT, t_start)
        except Exception as e:
            logger.warning("Tier 2 SLM inference failed: %s", e)
            return self._safe_fallback(raw_transcript, RepairStatus.FALLBACK_ERROR, t_start)

        # Tier 3: Slot Restoration (< 2 ms) & Slot Completeness Verification
        missing_slots = SlotLocker.find_missing_slots(raw_generated, slots)
        duplicated_slots = SlotLocker.find_duplicated_slots(raw_generated, slots)
        restored_text = SlotLocker.restore(raw_generated, slots)
        unexpanded_slots = re.findall(r"<SLOT_\d+>", restored_text)

        # FactGuard Veto Check: Ensure zero missing critical facts, negations, or locked slots
        elapsed_ms = (time.perf_counter() - t_start) * 1000.0
        if elapsed_ms > self.MAX_LATENCY_MS:
            logger.info("Local text repair timed out (%.1f ms > %.1f ms); vetoing.", elapsed_ms, self.MAX_LATENCY_MS)
            return self._safe_fallback(raw_transcript, RepairStatus.FALLBACK_TIMEOUT, t_start)

        facts = verify_critical_facts(raw_transcript, restored_text, language=language)
        missing_critical = list(dict.fromkeys(facts["missing_numbers"] + facts["missing_negations"] + missing_slots))
        added_critical = list(dict.fromkeys(
            [v for vals in facts["added_entities"].values() for v in vals] + duplicated_slots + unexpanded_slots
        ))

        if missing_critical or added_critical:
            veto_reason = f"FactGuard veto: missing={missing_critical}, added={added_critical}"
            logger.warning("Local text repair rejected: %s", veto_reason)
            return RepairResult(
                status=RepairStatus.VETOED_FACT_MISMATCH,
                text=raw_transcript,
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
