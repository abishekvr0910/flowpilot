"""
FlowPilot Local Text Repair Engine (Spec 0004: Feature 30 Sandbox)
Bounded natural language text repair, punctuation restoration, and disfluency cleanup.

STRICT INVARIANTS:
1. Text repair ONLY (post-ASR NLP); NOT an acoustic speech recognizer.
2. Three-Tier Guard Protocol: Slot-locking (numbers, dates, negations, identifiers,
   literal @N placeholders, and filler-in-meaning mentions)
   + Bounded Span-Diff Infilling + FactGuard Veto Verification.
3. Hard execution deadline (400 ms). Fallback to raw Whisper on ANY error or veto in <= 5 ms.
4. Process Isolation: SLM runs in an isolated worker process that can be forcibly
   terminated (SIGTERM/kill) if native C++ inference hangs, eliminating thread leakage.
5. Asynchronous Non-Blocking Warmup: Model preloading executes asynchronously without
   stalling application startup or real-time dictation.
6. 100% offline, zero cloud egress.
"""

import gc
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
    VETOED_INSTRUCTION_EXECUTION = "VETOED_INSTRUCTION_EXECUTION"  # Model answered/executed instruction instead of cleaning text
    VETOED_TEMPLATE_LEAKAGE = "VETOED_TEMPLATE_LEAKAGE"  # Model leaked chat template tokens or prompt phrases


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
    Locks literal @N / <SLOT_N> tokens, filler-in-meaning mentions, code identifiers,
    numbers, currency, dates, and critical negations behind opaque placeholder tokens
    (<SLOT_N>) so hallucination or collision is impossible.
    """

    # Protect literal @0, @1, or <SLOT_0> in user input from colliding with compact slot encoding
    LITERAL_PLACEHOLDER_PATTERN = re.compile(r"(?:@\d+\b|<SLOT_\d+>)")

    # Protect filler words when used as a grammatical subject at sentence start (e.g., "um is a filler word")
    SUBJECT_FILLER_PATTERN = re.compile(
        r"^\s*\b(um|uh|er|ah)\b(?=\s+(?:is|was|means|appears|counts|has|isn't|wasn't|doesn't)\b)",
        re.IGNORECASE
    )

    # Protect filler words when mentioned meta-linguistically or quoted (e.g., "the word um", "'um'", '"uh"')
    MENTIONED_FILLER_PATTERN = re.compile(
        r"""(?:['"](?:um|uh|er|ah)['"]|(?<=\bword\s)(?:um|uh|er|ah)\b|(?<=\btoken\s)(?:um|uh|er|ah)\b|(?<=\bfiller\s)(?:um|uh|er|ah)\b|(?<=\bstring\s)(?:um|uh|er|ah)\b|(?<=\bliteral\s)(?:um|uh|er|ah)\b)""",
        re.IGNORECASE
    )

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

    SLOT_TOKEN_PATTERN = re.compile(r"<SLOT_(\d+)>")
    COMPACT_SLOT_PATTERN = re.compile(r"@(\d+)\b")

    @classmethod
    def lock(cls, text: str) -> Tuple[str, Dict[str, str]]:
        slots: Dict[str, str] = {}
        slot_idx = 0

        def replacer(match):
            nonlocal slot_idx
            matched_text = match.group(0)
            token = f"<SLOT_{slot_idx}>"
            slots[token] = matched_text
            slot_idx += 1
            return token

        locked = cls.LITERAL_PLACEHOLDER_PATTERN.sub(replacer, text)
        locked = cls.SUBJECT_FILLER_PATTERN.sub(replacer, locked)
        locked = cls.MENTIONED_FILLER_PATTERN.sub(replacer, locked)
        locked = cls.CODE_IDENTIFIER_PATTERN.sub(replacer, locked)
        locked = cls.NUMBER_PATTERN.sub(replacer, locked)
        locked = cls.NEGATION_PATTERN.sub(replacer, locked)

        return locked, slots

    @classmethod
    def to_compact_slots(cls, text: str) -> str:
        """Compresses <SLOT_N> (5 BPE subwords) into @N (2 BPE subwords) for bounded span repair."""
        return cls.SLOT_TOKEN_PATTERN.sub(r"@\1", text)

    @classmethod
    def from_compact_slots(cls, text: str) -> str:
        """Expands compact @N placeholders back into canonical <SLOT_N> tokens."""
        return cls.COMPACT_SLOT_PATTERN.sub(r"<SLOT_\1>", text)

    @classmethod
    def restore(cls, text: str, slots: Dict[str, str]) -> str:
        normalized = cls.from_compact_slots(text)
        # If the sentence begins with a natural-language negation or subject-filler slot
        # (e.g. 'neither', 'um'), capitalize its leading character while keeping code identifiers untouched.
        first_token_match = re.match(r"^\s*(<SLOT_\d+>)", normalized)
        capitalize_first_token = None
        if first_token_match:
            tok = first_token_match.group(1)
            orig = slots.get(tok, "")
            if orig and orig[0].islower() and (
                cls.NEGATION_PATTERN.fullmatch(orig)
                or orig.lower() in {"um", "uh", "er", "ah"}
            ):
                capitalize_first_token = tok

        def single_pass_restore(match):
            token = match.group(0)
            if token not in slots:
                return token
            original = slots[token]
            if token == capitalize_first_token and original and original[0].islower():
                return original[0].upper() + original[1:]
            return original

        return cls.SLOT_TOKEN_PATTERN.sub(single_pass_restore, normalized)

    @classmethod
    def find_missing_slots(cls, generated_text: str, slots: Dict[str, str]) -> List[str]:
        """Returns original values of any locked <SLOT_N> tokens dropped by the SLM."""
        normalized = cls.from_compact_slots(generated_text)
        return [original for token, original in slots.items() if token not in normalized]

    @classmethod
    def find_duplicated_slots(cls, generated_text: str, slots: Dict[str, str]) -> List[str]:
        """Returns original values of any locked <SLOT_N> tokens duplicated by the SLM."""
        normalized = cls.from_compact_slots(generated_text)
        return [original for token, original in slots.items() if normalized.count(token) > 1]


class SpanDiffEditor:
    """
    Tier 2 Bounded Span-Diff Editor.
    Instead of regenerating an entire multi-clause sentence token-by-token on CPU
    (which takes >1,300 ms and risks dropping later slots), extracts the dirty opening
    span (3 words when a leading filler is present, 2 words otherwise) for SLM repair
    (<=6 completion tokens, ~140 ms on CPU) and splices the repaired span back onto
    the slot-locked body.
    """

    # Only lowercase 'um' and 'uh' are treated as unguarded tail fillers;
    # uppercase acronyms/units ('ER', 'Ah', 'UH') and SlotLocker-protected mentions are preserved.
    FILLER_WORDS = {"um", "uh"}
    INTERROGATIVE_STARTERS = {
        "why", "how", "what", "when", "where", "who", "whom", "whose", "which",
        "can", "could", "should", "would", "will", "shall", "did", "does", "is", "are", "was", "were"
    }
    SPAN_WINDOW_WORDS = 3
    SPAN_THRESHOLD_WORDS = 2
    SPAN_MAX_TOKENS = 6

    @classmethod
    def extract_span(cls, locked_text: str) -> Tuple[str, str, bool]:
        """
        Splits locked_text into (slm_input_span, untouched_body_tail, is_windowed).
        For sentences > SPAN_THRESHOLD_WORDS, extracts a 3-word opening span when a leading
        disfluency filler is present (or 2-word opening span when no leading filler is present)
        with @N compact slot encoding, and strips isolated lowercase filler tokens from the tail.
        """
        words = locked_text.strip().split()
        if len(words) <= cls.SPAN_THRESHOLD_WORDS:
            return SlotLocker.to_compact_slots(locked_text.strip()), "", False

        has_leading_filler = any(
            w.strip(",.?!").lower() in cls.FILLER_WORDS
            for w in words[:cls.SPAN_WINDOW_WORDS]
        )
        window_size = cls.SPAN_WINDOW_WORDS if has_leading_filler else 2
        head_words = words[:window_size]
        tail_words = [
            w for w in words[window_size:]
            if w.strip(",.?!").lower() not in cls.FILLER_WORDS
        ]
        head_span = SlotLocker.to_compact_slots(" ".join(head_words))
        body_tail = " ".join(tail_words)
        return head_span, body_tail, True

    @classmethod
    def estimate_max_tokens(cls, head_span: str) -> int:
        """Dynamically bounds completion tokens for the extracted opening span."""
        content_words = [
            w for w in head_span.strip().split()
            if w.strip(",.?!").lower() not in cls.FILLER_WORDS
        ]
        tok_budget = sum(2 if re.fullmatch(r"@\d+", w) else 1 for w in content_words) + 1
        return max(2, min(cls.SPAN_MAX_TOKENS, tok_budget))

    @classmethod
    def assemble(cls, repaired_span: str, body_tail: str, is_windowed: bool, original_head_span: str = "") -> str:
        """Splices the SLM-repaired opening span onto the untouched slot-locked body tail."""
        expanded_head = SlotLocker.from_compact_slots(repaired_span.strip())
        if not is_windowed:
            return expanded_head

        # Remove premature terminal punctuation from the head span before splicing
        clean_head = expanded_head.rstrip(".?!")

        # Verify non-filler content words in the opening span were preserved by the SLM
        # (only when all <SLOT_N> tokens in the head span are intact, so dropped slots still trigger Tier-3 VETO)
        if original_head_span:
            orig_expanded = SlotLocker.from_compact_slots(original_head_span.strip())
            orig_slots = re.findall(r"<SLOT_\d+>", orig_expanded)
            actual_slots = re.findall(r"<SLOT_\d+>", clean_head)
            if orig_slots == actual_slots:
                expected_content = [
                    w for w in orig_expanded.split()
                    if w.strip(",.?!").lower() not in cls.FILLER_WORDS
                ]
                actual_content = [
                    w for w in clean_head.split()
                    if w.strip(",.?!").lower() not in cls.FILLER_WORDS
                ]
                if [w.strip(",.?!").lower() for w in actual_content] != [w.strip(",.?!").lower() for w in expected_content]:
                    if expected_content:
                        first = expected_content[0]
                        if first and first[0].islower() and not first.startswith("<SLOT_"):
                            first = first[0].upper() + first[1:]
                        clean_head = " ".join([first] + expected_content[1:])
                    else:
                        clean_head = orig_expanded
                elif len(actual_content) > 1 and len(actual_content) == len(expected_content):
                    # Preserve original casing for non-initial words (e.g. prevent '@0 Must' or 'I\'m The')
                    fixed_words = [actual_content[0]]
                    for act_w, exp_w in zip(actual_content[1:], expected_content[1:]):
                        if exp_w.islower() and not act_w.startswith("<SLOT_"):
                            fixed_words.append(exp_w)
                        else:
                            fixed_words.append(act_w)
                    clean_head = " ".join(fixed_words)

        assembled = f"{clean_head} {body_tail}".strip() if body_tail else clean_head
        if assembled and assembled[-1] not in ".?!":
            first_word = clean_head.split()[0].lower().strip(",.") if clean_head.split() else ""
            second_word = clean_head.split()[1].lower().strip(",.") if len(clean_head.split()) > 1 else ""
            is_question = (
                first_word in cls.INTERROGATIVE_STARTERS
                or (first_word == "do" and second_word in {"we", "you", "they", "i", "he", "she", "it"})
            )
            assembled += "?" if is_question else "."
        return assembled


class InstructionExecutionGuard:
    """
    Tier 3 Guard: Prevents conversational takeover, prompt fulfillment, and template leakage.
    If the speaker dictates an instruction (e.g. 'Write an email to John...'), an SLM
    might hallucinate an email rather than preserving the spoken words.
    This guard deterministically detects and vetoes instruction fulfillment and template leakage.
    """
    PREAMBLE_PATTERN = re.compile(
        r"^\s*(?:sure|certainly|absolutely|here(?:'s|\s+is)|i(?:'d|\s+would)\s+be\s+happy\s+to|i\s+can|of\s+course)\b",
        re.IGNORECASE
    )

    INSTRUCTION_MARKERS = {
        "ask", "answer", "compose", "create", "draft", "email", "generate",
        "make", "message", "prompt", "reply", "respond", "response", "summarize",
        "tell", "translate", "write", "claude", "chatgpt", "ai", "llm"
    }

    STOP_WORDS = {
        "a", "an", "and", "are", "as", "at", "be", "but", "by", "can", "could",
        "for", "from", "had", "has", "have", "he", "her", "him", "his", "i", "if",
        "in", "into", "is", "it", "its", "just", "me", "my", "of", "on", "or", "our",
        "please", "she", "so", "that", "the", "their", "them", "then", "there", "this",
        "to", "um", "uh", "was", "we", "were", "what", "when", "where", "who", "with",
        "would", "you", "your"
    }

    TEMPLATE_LEAKAGE_PATTERN = re.compile(
        r"(?:<\|im_start\|>|<\|im_end\|>|<\|begin_of_text\|>|<\|end_of_text\|>|\[INST\]|\[/INST\]|system\s*\n|assistant\s*\n|user\s*\n|Remove speech fillers|Keep @N and all other words)",
        re.IGNORECASE
    )

    @classmethod
    def significant_tokens(cls, text: str) -> set:
        normalized = text.lower()
        parts = re.findall(r"\b[a-z0-9_]+\b", normalized)
        return {p for p in parts if len(p) > 1 and p not in cls.STOP_WORDS}

    @classmethod
    def has_template_leakage(cls, text: str) -> bool:
        """Returns True if text contains raw chat template tokens or leaked prompt phrases."""
        return bool(cls.TEMPLATE_LEAKAGE_PATTERN.search(text))

    @classmethod
    def appears_to_have_executed_instruction(cls, raw_transcript: str, cleaned_transcript: str) -> bool:
        """
        Returns True if the output indicates the model executed the transcript
        as an instruction rather than performing literal text repair.
        """
        raw_clean = raw_transcript.strip()
        cleaned_clean = cleaned_transcript.strip()
        if not raw_clean or not cleaned_clean:
            return False

        # 1. Preamble check: model started with assistant conversational response
        cleaned_has_preamble = bool(cls.PREAMBLE_PATTERN.search(cleaned_clean))
        raw_has_preamble = bool(cls.PREAMBLE_PATTERN.search(raw_clean))
        if cleaned_has_preamble and not raw_has_preamble:
            return True

        # 2. Token overlap and instruction verb collapse
        raw_tokens = cls.significant_tokens(raw_clean)
        cleaned_tokens = cls.significant_tokens(cleaned_clean)
        if not raw_tokens or not cleaned_tokens:
            return False

        raw_markers = raw_tokens.intersection(cls.INSTRUCTION_MARKERS)
        if raw_markers:
            preserved_markers = raw_markers.intersection(cleaned_tokens)
            overlap = raw_tokens.intersection(cleaned_tokens)
            overlap_ratio = len(overlap) / max(len(raw_tokens), 1)

            # If the user spoke instruction words, but NONE survived and overlap plummeted below 35%
            if not preserved_markers and overlap_ratio < 0.35:
                return True

        return False


DEFAULT_SYSTEM_PROMPT = (
    "Remove speech fillers (um, uh) and capitalize the first word. Keep @N and all other words exact.\n"
    "User: um we must\n"
    "Assistant: We must\n"
    "User: uh do @0\n"
    "Assistant: Do @0\n"
    "User: @0 must\n"
    "Assistant: @0 must"
)


def _slm_process_worker_entry(pipe: Connection, model_path: Optional[str], n_threads: int):
    """
    Independent worker process entry point for local SLM inference.
    Runs in a dedicated OS process to allow hard termination if native C++ inference hangs.
    """
    llm = None
    infer_count = 0
    try:
        if os.name == "nt":
            try:
                import psutil
                psutil.Process(os.getpid()).nice(psutil.ABOVE_NORMAL_PRIORITY_CLASS)
            except Exception:
                pass
        if model_path:
            from llama_cpp import Llama
            llm = Llama(
                model_path=model_path,
                n_ctx=256,
                n_batch=128,
                n_threads=n_threads,
                use_mmap=True,
                logits_all=False,
                verbose=False
            )
            warmup_prompt = (
                f"<|im_start|>system\n{DEFAULT_SYSTEM_PROMPT}<|im_end|>\n"
                "<|im_start|>user\num test<|im_end|>\n<|im_start|>assistant\n"
            )
            llm(warmup_prompt, max_tokens=1, stop=["<|im_end|>", "\n"], temperature=0.0)
            gc.collect()
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
                infer_count += 1
                # Fast gen-0 collection after each call (<0.05 ms); full collection only when pipe is idle
                gc.collect(0)
                if infer_count % 25 == 0 and not pipe.poll(0):
                    gc.collect()

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
    MAX_TOKENS: int = 60            # Upper bound for full-sentence fallback

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.enabled: bool = bool(self.config.get("local_text_repair_enabled", False))
        self.model_path: Optional[str] = self.config.get("local_text_repair_model_path")
        self.worker_mode: str = self.config.get("local_text_repair_worker_mode", "process")
        self.span_diff_enabled: bool = bool(self.config.get("local_text_repair_span_diff", True))

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

    def unload_model(self) -> bool:
        """
        Releases the local SLM worker process and memory during idle periods.
        Reclaims system RAM when no text repair has been requested.
        """
        if self._worker_process is not None:
            self._terminate_worker_process()
            import gc
            gc.collect()
            return True
        return False

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

    def _infer_bounded(self, prompt: str, remaining_ms: float, max_tokens: Optional[int] = None) -> str:
        """
        Executes inference within remaining_ms.
        If self._llm is set (mock/thread mode), runs via ThreadPoolExecutor.
        Otherwise, runs via isolated worker process with hard process termination on timeout.
        """
        remaining_sec = remaining_ms / 1000.0
        tokens_limit = max_tokens if max_tokens is not None else self.MAX_TOKENS

        # Mode A: In-process callable (used for unit tests and mock overrides)
        if self._llm is not None:
            executor = self._get_executor()
            future = executor.submit(
                self._llm,
                prompt,
                max_tokens=tokens_limit,
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
            "max_tokens": tokens_limit,
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
        Tier 1: Slot-lock literal @N tokens, filler-in-meaning mentions, numbers, dates, negations, identifiers.
        Tier 2: Bounded Span-Diff infilling via local SLM with hard process-isolated deadline enforcement.
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

        # Tier 2: Bounded Local SLM Span-Diff Infilling with Process-Isolated Hard Timeout
        try:
            time_spent_ms = (time.perf_counter() - t_start) * 1000.0
            remaining_ms = self.MAX_LATENCY_MS - time_spent_ms
            if remaining_ms <= 5.0:
                return self._safe_fallback(raw_transcript, RepairStatus.FALLBACK_TIMEOUT, t_start)

            if self.span_diff_enabled:
                slm_span, body_tail, is_windowed = SpanDiffEditor.extract_span(locked_text)
                max_toks = SpanDiffEditor.estimate_max_tokens(slm_span)
            else:
                slm_span, body_tail, is_windowed = locked_text, "", False
                max_toks = self.MAX_TOKENS

            system_prompt = DEFAULT_SYSTEM_PROMPT
            prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{slm_span}<|im_end|>\n<|im_start|>assistant\n"

            raw_span_generated = self._infer_bounded(prompt, remaining_ms, max_tokens=max_toks)
            raw_generated = SpanDiffEditor.assemble(
                raw_span_generated,
                body_tail,
                is_windowed,
                original_head_span=slm_span if is_windowed else "",
            )

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
        # Check if any unexpanded <SLOT_N> remains that wasn't a literal <SLOT_N> in the original input
        literal_slot_tokens = [v for v in slots.values() if re.fullmatch(r"<SLOT_\d+>", v)]
        unexpanded_slots = [
            tok for tok in re.findall(r"<SLOT_\d+>", restored_text)
            if tok not in literal_slot_tokens
        ]

        # FactGuard Veto Check: Ensure zero missing critical facts, negations, or locked slots
        elapsed_ms = (time.perf_counter() - t_start) * 1000.0
        if elapsed_ms > self.MAX_LATENCY_MS:
            logger.info("Local text repair timed out (%.1f ms > %.1f ms); vetoing.", elapsed_ms, self.MAX_LATENCY_MS)
            return self._safe_fallback(raw_transcript, RepairStatus.FALLBACK_TIMEOUT, t_start)

        # Instruction Execution & Template Leakage Guards
        if InstructionExecutionGuard.has_template_leakage(restored_text):
            veto_reason = "InstructionExecutionGuard veto: detected template token leakage in output"
            logger.warning("Local text repair rejected: %s", veto_reason)
            return RepairResult(
                status=RepairStatus.VETOED_TEMPLATE_LEAKAGE,
                text=raw_transcript,
                raw_input=raw_transcript,
                latency_ms=elapsed_ms,
                veto_reason=veto_reason,
                slots_locked=len(slots),
                fallback_used=True
            )

        if InstructionExecutionGuard.appears_to_have_executed_instruction(raw_transcript, restored_text):
            veto_reason = "InstructionExecutionGuard veto: model answered/executed instruction instead of cleaning text"
            logger.warning("Local text repair rejected: %s", veto_reason)
            return RepairResult(
                status=RepairStatus.VETOED_INSTRUCTION_EXECUTION,
                text=raw_transcript,
                raw_input=raw_transcript,
                latency_ms=elapsed_ms,
                veto_reason=veto_reason,
                slots_locked=len(slots),
                fallback_used=True
            )

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
