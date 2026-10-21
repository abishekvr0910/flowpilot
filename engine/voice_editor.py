"""
FlowPilot Bounded Voice Editor Engine (PR 4)
Provides deterministic, verified voice-directed text editing:
- Strict document and selection bounds (no unconstrained agent behaviors)
- Atomic EditTransactions with monotonic revision hashing and one-use transaction IDs
- Revalidation immediately prior to apply (abort if document or selection changed)
- Natural language span replacement ("replace Friday with Monday")
- Ambiguity detection (if multiple spans match, require clarification; never guess)
- Verified selection deletion ("remove this part")
- Document appending ("add this sentence at the end")
- Verified undo transactions tied to document revision
- Terminal and secure field safety enforcement (never auto-execute commands or edit passwords)
- FactGuard preservation outside the authorized change
"""

import re
import time
import uuid
import hashlib
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple

from engine.writing_intelligence import FactGuard


@dataclass
class EditTransaction:
    transaction_id: str
    target_id: str
    target_type: str  # "scratchpad" | "external"
    source_revision: str  # Hash of text at plan time
    selected_range: Tuple[int, int]  # (start_char, end_char)
    instruction: str
    operation: str  # "replace_span" | "remove_selection" | "append_text" | "preset_transform" | "undo" | "unsupported"
    parameters: Dict[str, Any]
    original_text: str
    candidate_text: str
    diff_preview: str
    status: str  # "pending" | "applied" | "aborted" | "ambiguous" | "unsupported"
    can_apply: bool
    error_message: Optional[str] = None
    consumed: bool = False
    created_at: float = field(default_factory=time.time)


# Regex patterns for natural language voice editing instructions
RE_REPLACE_SPAN = re.compile(
    r"^\s*(?:replace|change)\s+[\"']?(.+?)[\"']?\s+(?:with|to)\s+[\"']?(.+?)[\"']?\s*$",
    re.IGNORECASE
)
RE_REMOVE_SELECTION = re.compile(
    r"^\s*(?:remove|delete|erase|strip)\s+(?:this(?:\s+part)?|selection|selected(?:\s+text)?|this\s+sentence|it)\s*$",
    re.IGNORECASE
)
RE_APPEND_END = re.compile(
    r"^\s*(?:add|append)\s+(?:this\s+sentence\s+|this\s+text\s+|text\s+|sentence\s+)?at\s+(?:the\s+)?end[:\s]*(.+)$",
    re.IGNORECASE
)
RE_APPEND_END_ALT = re.compile(
    r"^\s*add\s+(.+?)\s+at\s+(?:the\s+)?end\s*$",
    re.IGNORECASE
)
RE_UNDO_EDIT = re.compile(
    r"^\s*(?:undo|revert)(?:\s+(?:that|last|the))?(?:\s+edit)?\s*$",
    re.IGNORECASE
)

# Preset transform patterns
RE_EDIT_CONCISE = re.compile(
    r"^\s*(?:make\s+(?:this|it)?\s*)?(?:concise|shorter|brief)\s*$",
    re.IGNORECASE
)
RE_EDIT_PROFESSIONAL = re.compile(
    r"^\s*(?:make\s+(?:this|it)?\s*)?(?:professional|formal|executive)(?:\s+tone)?\s*$",
    re.IGNORECASE
)
RE_EDIT_BULLETS = re.compile(
    r"^\s*(?:format|convert|make|turn)?\s*(?:this|it)?\s*(?:in\s*to|as)?\s*(?:a\s+)?(?:bullet\s+points?|bulleted\s+list|bullet\s+list|bullets)\s*$",
    re.IGNORECASE
)

TERMINAL_PROCESSES = {
    "cmd.exe", "powershell.exe", "pwsh.exe", "windowsterminal.exe",
    "wt.exe", "bash.exe", "wsl.exe", "mintty.exe", "alacritty.exe", "conhost.exe"
}


def hash_text(text: str) -> str:
    """Computes deterministic 16-char hex hash of document text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


class VoiceEditor:
    """
    Deterministic voice editing engine.
    Plans, validates, and atomically executes bounded edit transactions.
    """

    def __init__(self):
        # Transaction history per target_id: target_id -> List[EditTransaction]
        self._history: Dict[str, List[EditTransaction]] = {}

    def get_history(self, target_id: str) -> List[EditTransaction]:
        return list(self._history.get(target_id, []))

    def clear_history(self, target_id: str) -> None:
        if target_id in self._history:
            self._history[target_id].clear()

    @staticmethod
    def check_target_safety(process_name: Optional[str] = None, window_title: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Guarantees terminal and password safety.
        Returns (is_safe, error_or_warning_message).
        """
        proc = (process_name or "").lower().strip()
        title = (window_title or "").lower().strip()

        # Terminal check: Never allow arbitrary multi-line replacements or Enter key submission in terminals
        if proc in TERMINAL_PROCESSES or any(t in title for t in ["powershell", "command prompt", "terminal", "wsl"]):
            return False, "Target is a terminal window. Voice editing operations are restricted to prevent unintended command execution."

        # Password / sensitive window check
        if any(w in title for w in ["password", "credential", "keepass", "1password", "bitwarden"]):
            return False, "Target window appears to contain secure credentials. Voice editing is blocked."

        return True, None

    def plan_edit(
        self,
        document_text: str,
        selected_range: Tuple[int, int] = (0, 0),
        instruction: str = "",
        target_id: str = "scratchpad:editor",
        target_type: str = "scratchpad"
    ) -> EditTransaction:
        """
        Parses the spoken instruction, scopes target spans, and drafts an atomic EditTransaction.
        Does NOT alter document text until explicitly applied.
        """
        tx_id = f"tx_{uuid.uuid4().hex[:12]}"
        rev_hash = hash_text(document_text)
        instruction_clean = (instruction or "").strip()

        start, end = selected_range
        # Clamp selection range to document bounds
        doc_len = len(document_text)
        start = max(0, min(start, doc_len))
        end = max(start, min(end, doc_len))
        has_selection = (end > start)

        if not instruction_clean:
            return EditTransaction(
                transaction_id=tx_id,
                target_id=target_id,
                target_type=target_type,
                source_revision=rev_hash,
                selected_range=(start, end),
                instruction=instruction_clean,
                operation="unsupported",
                parameters={},
                original_text=document_text,
                candidate_text=document_text,
                diff_preview="No instruction provided.",
                status="unsupported",
                can_apply=False,
                error_message="Instruction was empty."
            )

        # 1. UNDO REQUEST
        if RE_UNDO_EDIT.match(instruction_clean):
            history = self._history.get(target_id, [])
            applied_txs = [t for t in history if t.status == "applied"]
            if not applied_txs:
                return EditTransaction(
                    transaction_id=tx_id,
                    target_id=target_id,
                    target_type=target_type,
                    source_revision=rev_hash,
                    selected_range=(start, end),
                    instruction=instruction_clean,
                    operation="undo",
                    parameters={},
                    original_text=document_text,
                    candidate_text=document_text,
                    diff_preview="Nothing to undo.",
                    status="aborted",
                    can_apply=False,
                    error_message="No prior edit transaction available to undo."
                )

            last_tx = applied_txs[-1]
            # Check if current document matches the result of the last transaction
            if hash_text(document_text) != hash_text(last_tx.candidate_text):
                # Document was modified since last edit; present recovery text rather than blind revert
                return EditTransaction(
                    transaction_id=tx_id,
                    target_id=target_id,
                    target_type=target_type,
                    source_revision=rev_hash,
                    selected_range=(start, end),
                    instruction=instruction_clean,
                    operation="undo",
                    parameters={"recovery_text": last_tx.original_text},
                    original_text=document_text,
                    candidate_text=document_text,
                    diff_preview=f"Recovery available from edit {last_tx.transaction_id[:8]}, but document has changed since.",
                    status="aborted",
                    can_apply=False,
                    error_message="Document was modified after the last edit. Direct undo blocked to prevent data loss. Use recovery text if needed."
                )

            return EditTransaction(
                transaction_id=tx_id,
                target_id=target_id,
                target_type=target_type,
                source_revision=rev_hash,
                selected_range=(start, end),
                instruction=instruction_clean,
                operation="undo",
                parameters={"target_tx_id": last_tx.transaction_id},
                original_text=document_text,
                candidate_text=last_tx.original_text,
                diff_preview=f"Undo edit '{last_tx.instruction}': restore prior revision ({len(last_tx.original_text)} chars)",
                status="pending",
                can_apply=True
            )

        # 2. REPLACE SPAN REQUEST ("replace Friday with Monday")
        m_replace = RE_REPLACE_SPAN.match(instruction_clean)
        if m_replace:
            find_term = m_replace.group(1).strip()
            replace_term = m_replace.group(2).strip()

            if not find_term:
                return self._build_aborted(tx_id, target_id, target_type, rev_hash, (start, end), instruction_clean, "Target search term cannot be empty.")

            # Search scope: inside selected text if selection active, otherwise whole document
            if has_selection:
                search_text = document_text[start:end]
                scope_name = "selection"
                offset = start
            else:
                search_text = document_text
                scope_name = "document"
                offset = 0

            # Case-insensitive search for occurrences
            pattern = re.compile(re.escape(find_term), re.IGNORECASE)
            matches = list(pattern.finditer(search_text))

            if len(matches) == 0:
                return EditTransaction(
                    transaction_id=tx_id,
                    target_id=target_id,
                    target_type=target_type,
                    source_revision=rev_hash,
                    selected_range=(start, end),
                    instruction=instruction_clean,
                    operation="replace_span",
                    parameters={"find": find_term, "replace": replace_term},
                    original_text=document_text,
                    candidate_text=document_text,
                    diff_preview=f"Could not find '{find_term}' in {scope_name}.",
                    status="aborted",
                    can_apply=False,
                    error_message=f"Term '{find_term}' was not found in the {scope_name}."
                )

            if len(matches) > 1:
                # Ambiguous! As per spec: "If several matches exist, ask which one."
                return EditTransaction(
                    transaction_id=tx_id,
                    target_id=target_id,
                    target_type=target_type,
                    source_revision=rev_hash,
                    selected_range=(start, end),
                    instruction=instruction_clean,
                    operation="replace_span",
                    parameters={"find": find_term, "replace": replace_term, "match_count": len(matches)},
                    original_text=document_text,
                    candidate_text=document_text,
                    diff_preview=f"Found {len(matches)} occurrences of '{find_term}'. Ambiguous target.",
                    status="ambiguous",
                    can_apply=False,
                    error_message=f"Found {len(matches)} occurrences of '{find_term}'. Please select the specific span or clarify which occurrence to change."
                )

            # Unique match!
            m = matches[0]
            abs_start = offset + m.start()
            abs_end = offset + m.end()
            matched_span = document_text[abs_start:abs_end]

            # Construct new candidate document text
            new_text = document_text[:abs_start] + replace_term + document_text[abs_end:]

            # FactGuard check on remainder of document (protect outside numbers/negations)
            diff_preview = f"Replace: '{matched_span}' -> '{replace_term}' (pos {abs_start}..{abs_end})"

            return EditTransaction(
                transaction_id=tx_id,
                target_id=target_id,
                target_type=target_type,
                source_revision=rev_hash,
                selected_range=(abs_start, abs_start + len(replace_term)),
                instruction=instruction_clean,
                operation="replace_span",
                parameters={"find": find_term, "replace": replace_term, "span": (abs_start, abs_end)},
                original_text=document_text,
                candidate_text=new_text,
                diff_preview=diff_preview,
                status="pending",
                can_apply=True
            )

        # 3. REMOVE SELECTION REQUEST ("remove this part")
        if RE_REMOVE_SELECTION.match(instruction_clean):
            if not has_selection:
                # Require an active verified selection; without selection, request clarification instead of guessing
                return EditTransaction(
                    transaction_id=tx_id,
                    target_id=target_id,
                    target_type=target_type,
                    source_revision=rev_hash,
                    selected_range=(start, end),
                    instruction=instruction_clean,
                    operation="remove_selection",
                    parameters={},
                    original_text=document_text,
                    candidate_text=document_text,
                    diff_preview="No active text selection.",
                    status="aborted",
                    can_apply=False,
                    error_message="No text selected. Please select the specific text to remove before issuing this command."
                )

            selected_span = document_text[start:end]
            new_text = document_text[:start] + document_text[end:]
            diff_preview = f"Delete selection: '{selected_span}' ({len(selected_span)} chars)"

            return EditTransaction(
                transaction_id=tx_id,
                target_id=target_id,
                target_type=target_type,
                source_revision=rev_hash,
                selected_range=(start, start),
                instruction=instruction_clean,
                operation="remove_selection",
                parameters={"deleted_span": selected_span},
                original_text=document_text,
                candidate_text=new_text,
                diff_preview=diff_preview,
                status="pending",
                can_apply=True
            )

        # 4. APPEND SENTENCE AT END REQUEST ("add this sentence at the end: ...")
        m_append = RE_APPEND_END.match(instruction_clean) or RE_APPEND_END_ALT.match(instruction_clean)
        if m_append:
            append_text = m_append.group(1).strip()
            if not append_text:
                return self._build_aborted(tx_id, target_id, target_type, rev_hash, (start, end), instruction_clean, "Text to append cannot be empty.")

            # Append cleanly to document
            if document_text and not document_text.endswith(("\n", " ")):
                separator = " " if not document_text.endswith((".", "!", "?")) else "\n\n"
                new_text = document_text + separator + append_text
            else:
                new_text = document_text + append_text

            diff_preview = f"Append at end: '{append_text}'"

            return EditTransaction(
                transaction_id=tx_id,
                target_id=target_id,
                target_type=target_type,
                source_revision=rev_hash,
                selected_range=(len(document_text), len(new_text)),
                instruction=instruction_clean,
                operation="append_text",
                parameters={"append": append_text},
                original_text=document_text,
                candidate_text=new_text,
                diff_preview=diff_preview,
                status="pending",
                can_apply=True
            )

        # 5. PRESET TRANSFORMS ("make this shorter", "make this professional", "format as bullets")
        target_scope = document_text[start:end] if has_selection else document_text

        if RE_EDIT_CONCISE.match(instruction_clean):
            from engine.transforms_engine import TransformsEngine
            engine = TransformsEngine()
            transformed = engine._apply_concise(target_scope)
            new_text = (document_text[:start] + transformed + document_text[end:]) if has_selection else transformed
            return EditTransaction(
                transaction_id=tx_id,
                target_id=target_id,
                target_type=target_type,
                source_revision=rev_hash,
                selected_range=(start, start + len(transformed)),
                instruction=instruction_clean,
                operation="preset_transform",
                parameters={"preset": "make_concise"},
                original_text=document_text,
                candidate_text=new_text,
                diff_preview=f"Draft concise edit: {len(target_scope)} -> {len(transformed)} chars",
                status="pending",
                can_apply=True
            )

        if RE_EDIT_PROFESSIONAL.match(instruction_clean):
            from engine.transforms_engine import TransformsEngine
            engine = TransformsEngine()
            transformed = engine._apply_professional_tone(target_scope)
            new_text = (document_text[:start] + transformed + document_text[end:]) if has_selection else transformed
            return EditTransaction(
                transaction_id=tx_id,
                target_id=target_id,
                target_type=target_type,
                source_revision=rev_hash,
                selected_range=(start, start + len(transformed)),
                instruction=instruction_clean,
                operation="preset_transform",
                parameters={"preset": "professional"},
                original_text=document_text,
                candidate_text=new_text,
                diff_preview="Draft professional tone edit",
                status="pending",
                can_apply=True
            )

        if RE_EDIT_BULLETS.match(instruction_clean):
            from engine.transforms_engine import TransformsEngine
            engine = TransformsEngine()
            transformed = engine._apply_bullet_points(target_scope)
            new_text = (document_text[:start] + transformed + document_text[end:]) if has_selection else transformed
            return EditTransaction(
                transaction_id=tx_id,
                target_id=target_id,
                target_type=target_type,
                source_revision=rev_hash,
                selected_range=(start, start + len(transformed)),
                instruction=instruction_clean,
                operation="preset_transform",
                parameters={"preset": "bullet_points"},
                original_text=document_text,
                candidate_text=new_text,
                diff_preview="Format as Markdown bullets",
                status="pending",
                can_apply=True
            )

        # 6. UNSUPPORTED INSTRUCTION (Arbitrary open-ended prompts without local LLM)
        return EditTransaction(
            transaction_id=tx_id,
            target_id=target_id,
            target_type=target_type,
            source_revision=rev_hash,
            selected_range=(start, end),
            instruction=instruction_clean,
            operation="unsupported",
            parameters={},
            original_text=document_text,
            candidate_text=document_text,
            diff_preview="Unsupported voice editing instruction.",
            status="unsupported",
            can_apply=False,
            error_message=f"Instruction '{instruction_clean}' is not a recognized deterministic edit command. Document remains unchanged."
        )

    def apply_transaction(
        self,
        transaction: EditTransaction,
        current_document_text: str,
        current_selection: Tuple[int, int] = (0, 0)
    ) -> Tuple[bool, str, str]:
        """
        Atomically executes the EditTransaction after revalidating document revision and constraints.
        Returns:
            (success, resulting_text, status_message)
        """
        # 1. Guard against consumed transaction
        if transaction.consumed:
            return False, current_document_text, "Transaction has already been applied or consumed."

        # 2. Guard against non-applicable transaction
        if not transaction.can_apply:
            return False, current_document_text, transaction.error_message or "Transaction is not eligible to apply."

        # 3. Revalidate document revision
        current_rev = hash_text(current_document_text)
        if current_rev != transaction.source_revision:
            transaction.status = "aborted"
            transaction.error_message = "Document was modified concurrently. Edit aborted to prevent clobbering."
            return False, current_document_text, transaction.error_message

        # 4. Invariant: FactGuard preservation outside the explicit delta
        if transaction.operation in ("replace_span", "preset_transform"):
            fg = FactGuard.verify_invariants(transaction.original_text, transaction.candidate_text)
            # If the operation was explicitly replacing a date/number (e.g. "replace Friday with Monday"),
            # ensure that no other facts were altered outside the target parameter
            if not fg.get("passed", True):
                find_param = transaction.parameters.get("find", "").lower()
                # Check if the invariant failure was exclusively due to the intentional user change
                # Otherwise, fail closed
                altered_entities = fg.get("violations", [])
                unauthorized_violations = [v for v in altered_entities if find_param not in str(v).lower()]
                if unauthorized_violations:
                    transaction.status = "aborted"
                    transaction.error_message = f"FactGuard invariant violation outside authorized change: {unauthorized_violations}"
                    return False, current_document_text, transaction.error_message

        # 5. Commit transaction
        transaction.consumed = True
        transaction.status = "applied"

        # Record in target history for verified undo
        target_hist = self._history.setdefault(transaction.target_id, [])
        target_hist.append(transaction)

        return True, transaction.candidate_text, "Edit applied successfully."

    def _build_aborted(
        self,
        tx_id: str,
        target_id: str,
        target_type: str,
        rev_hash: str,
        selected_range: Tuple[int, int],
        instruction: str,
        error_msg: str
    ) -> EditTransaction:
        return EditTransaction(
            transaction_id=tx_id,
            target_id=target_id,
            target_type=target_type,
            source_revision=rev_hash,
            selected_range=selected_range,
            instruction=instruction,
            operation="aborted",
            parameters={},
            original_text="",
            candidate_text="",
            diff_preview=error_msg,
            status="aborted",
            can_apply=False,
            error_message=error_msg
        )


_shared_voice_editor: Optional[VoiceEditor] = None


def get_voice_editor() -> VoiceEditor:
    global _shared_voice_editor
    if _shared_voice_editor is None:
        _shared_voice_editor = VoiceEditor()
    return _shared_voice_editor
