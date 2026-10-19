"""
FlowPilot Guided AI Meeting Deliberation & Intelligence Engine
Inspired by agentic deliberation frameworks (Hermes Agent):
- "What Did I Miss?" Live Catch-Up Recap
- Multi-perspective Decision Weighing Matrix (Pros/Cons, Trade-Offs, Consensus vs Dissent)
- Risk & Blocker Radar with Severity Scoring
- Agentic Action Dispatcher (Follow-up Email Draft & Task Cards)
- Granular Retention Policy Enforcement (7, 30, 90, 365 days & Indefinite)
"""

import os
import re
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, NamedTuple


class CatchUpRecap:
    def __init__(
        self,
        session_title: str,
        time_window: str,
        recent_points: List[str],
        active_summary: str,
        immediate_action_items: Optional[List[str]] = None,
        window_minutes: int = 5,
        active_speakers_count: int = 1
    ):
        self.session_title = session_title
        self.time_window = time_window
        self.recent_points = recent_points
        self.active_summary = active_summary
        self.immediate_action_items = immediate_action_items or []
        self.window_minutes = window_minutes
        self.active_speakers_count = active_speakers_count

    @property
    def bullet_count(self) -> int:
        return len(self.recent_points)

    @property
    def summary_points(self) -> List[str]:
        return self.recent_points

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_title": self.session_title,
            "time_window": self.time_window,
            "recent_points": self.recent_points,
            "active_summary": self.active_summary,
            "immediate_action_items": self.immediate_action_items,
            "window_minutes": self.window_minutes,
            "active_speakers_count": self.active_speakers_count
        }


class DeliberationTopic:
    def __init__(
        self,
        topic: str,
        pros_agreements: List[str],
        cons_concerns: List[str],
        status: str = "CONSENSUS_REACHED"
    ):
        self.topic = topic
        self.pros_agreements = pros_agreements
        self.cons_concerns = cons_concerns
        self.status = status

    @property
    def title(self) -> str:
        return self.topic

    @property
    def pros(self) -> List[str]:
        return self.pros_agreements

    @property
    def cons(self) -> List[str]:
        return self.cons_concerns

    @property
    def consensus(self) -> str:
        return self.status if self.status == "CONSENSUS_REACHED" else ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic": self.topic,
            "pros_agreements": self.pros_agreements,
            "cons_concerns": self.cons_concerns,
            "status": self.status
        }


class RiskItem:
    def __init__(
        self,
        text: str,
        severity: str = "MEDIUM",
        mitigation_hint: str = ""
    ):
        self.text = text
        self.severity = severity.upper()
        self.mitigation_hint = mitigation_hint

    @property
    def description(self) -> str:
        return self.text

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "severity": self.severity,
            "mitigation_hint": self.mitigation_hint
        }


class TaskCard(dict):
    def __init__(self, title: str, markdown_body: str, priority: str = "Medium"):
        super().__init__(title=title, markdown_body=markdown_body, priority=priority)
        self.title = title
        self.markdown_body = markdown_body
        self.priority = priority

    def to_markdown(self) -> str:
        return self.markdown_body


class RetentionPolicy:
    VALID_POLICIES = ["indefinite", "7_days", "30_days", "90_days", "365_days"]
    POLICY_DAYS = {
        "7_days": 7,
        "30_days": 30,
        "90_days": 90,
        "365_days": 365,
        "indefinite": None
    }

    def __init__(self, meetings_dir: Optional[Path] = None, max_age_days: Optional[int] = None):
        self.meetings_dir = meetings_dir
        self.max_age_days = max_age_days

    def enforce(self) -> int:
        if not self.meetings_dir or self.max_age_days is None or self.max_age_days <= 0:
            return 0
        policy_key = f"{self.max_age_days}_days"
        purged = RetentionPolicy.enforce_retention(self.meetings_dir, policy_key)
        return len(purged)

    @classmethod
    def enforce_retention(cls, meetings_dir: Path, policy: str = "indefinite") -> List[str]:
        """
        Deletes meeting records older than the specified retention policy window.
        Returns the list of purged meeting IDs.
        """
        days = cls.POLICY_DAYS.get(policy)
        if days is None:
            return []

        cutoff_timestamp = time.time() - (days * 86400)
        purged = []

        if not meetings_dir.exists():
            return purged

        for f in meetings_dir.glob("*.json"):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                st = data.get("start_time")
                if st is None:
                    # Fallback to file modification time
                    st = f.stat().st_mtime
                if float(st) < cutoff_timestamp:
                    m_id = data.get("meeting_id", f.stem)
                    f.unlink(missing_ok=True)
                    purged.append(m_id)
            except Exception as e:
                print(f"[RetentionPolicy Error] Failed checking {f}: {e}")

        return purged


# Lexical heuristic patterns for deliberative weighting
PRO_PATTERNS = [
    r"\b(advantage|benefit|strength|pros|pro|favorable|ideal|faster|easier|scalable|robust|efficient|clean)\b",
    r"\b(major advantage|we like|prefer|agree with|supports|great|good choice|simplifies)\b"
]

CON_PATTERNS = [
    r"\b(however|but|risk|overhead|concern|downside|disadvantage|limitation|flaw|issue|bottleneck|problem)\b",
    r"\b(heavy|slow|complex|costly|migration risk|lock|leak|drawback|cause locks|unsupported)\b"
]

RISK_HIGH_PATTERNS = [
    r"\b(critical|security|compliance|vulnerability|data loss|corruption|outage|breach|deadlock)\b",
    r"\b(blocker|catastrophic|unacceptable|legal risk|regulatory)\b"
]

RISK_MEDIUM_PATTERNS = [
    r"\b(delay|debt|drift|overhead|dependency|unpinned|latency spike|warning|incompatible)\b",
    r"\b(budget|fragile|lock contention|flaky)\b"
]


class MeetingDeliberationEngine:
    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or (Path.home() / ".flowpilot" / "meetings")
        self.retention_policy = RetentionPolicy(meetings_dir=self.storage_dir)

    def enforce_retention_policy(self) -> int:
        return self.retention_policy.enforce()

    def _extract_session_data(self, session: Any) -> Tuple[str, List[Dict[str, Any]], List[str], List[Any]]:
        """Extract title, segments, decisions, and action items flexibly from object or dict."""
        if isinstance(session, dict):
            title = session.get("title", "Meeting")
            segs = session.get("segments", [])
            if not segs and session.get("transcript"):
                transcript = session.get("transcript", "")
                lines = [l.strip() for l in transcript.split("\n") if l.strip()]
                segs = [{"time": "00:00", "text": line, "timestamp": time.time()} for line in lines]
            decisions = list(session.get("decisions", []))
            actions = list(session.get("action_items", []))
            return title, segs, decisions, actions

        title = getattr(session, "title", "Meeting")
        segs = getattr(session, "segments", [])
        decisions = list(getattr(session, "decisions", []))
        actions = list(getattr(session, "action_items", []))

        if hasattr(session, "summary") and isinstance(session.summary, dict):
            if not segs:
                segs = session.summary.get("segments", [])
            if not decisions:
                decisions = list(session.summary.get("decisions", []))
            if not actions:
                actions = list(session.summary.get("action_items", []))
            if not segs and session.summary.get("transcript"):
                transcript = session.summary.get("transcript", "")
                lines = [l.strip() for l in transcript.split("\n") if l.strip()]
                segs = [{"time": "00:00", "text": line, "timestamp": time.time()} for line in lines]

        return title, segs, decisions, actions

    # -----------------------------------------------------------------------
    # 1. "What Did I Miss?" Live Catch-Up
    # -----------------------------------------------------------------------
    def generate_catchup(self, session: Any, window_seconds: float = 300.0) -> CatchUpRecap:
        """
        Extracts salient points from the last `window_seconds` of the meeting.
        """
        title, segments, _, actions = self._extract_session_data(session)
        if not segments:
            return CatchUpRecap(
                session_title=title,
                time_window="No speech recorded",
                recent_points=[],
                active_summary="Meeting has not recorded any speech segments yet.",
                immediate_action_items=[],
                window_minutes=int(window_seconds // 60),
                active_speakers_count=0
            )

        now = time.time()
        start_cut = now - window_seconds

        # Filter segments within the recent window
        is_fallback = False
        recent_segs = [s for s in segments if s.get("timestamp", now) >= start_cut]
        if not recent_segs:
            # Fallback to the last 4 segments if timestamps were simulated or outside range
            recent_segs = segments[-4:]
            is_fallback = True

        recent_texts = [s.get("text", "").strip() for s in recent_segs if s.get("text", "").strip()]
        start_time_label = recent_segs[0].get("time", "00:00")
        end_time_label = recent_segs[-1].get("time", "00:00")
        if is_fallback:
            time_window = f"Window {start_time_label} - {end_time_label} (Prior discussion preview)"
        else:
            time_window = f"Window {start_time_label} - {end_time_label} (Past {int(window_seconds // 60)} min)"

        # Highlight salient points (sentences with nouns, actions, or decisions)
        points = []
        for text in recent_texts:
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if len(s.strip()) > 10]
            for sent in sentences:
                if len(points) < 6:
                    points.append(sent)

        summary_preview = " ".join(points[:3]) if points else "Ongoing discussion."
        active_summary = f"Discussion focus: {summary_preview}"

        immediate_actions = [str(a) for a in actions[:3]]

        return CatchUpRecap(
            session_title=title,
            time_window=time_window,
            recent_points=points,
            active_summary=active_summary,
            immediate_action_items=immediate_actions,
            window_minutes=int(window_seconds // 60),
            active_speakers_count=1
        )

    # -----------------------------------------------------------------------
    # 2. Decision Weighing Matrix ("Weighing with AI")
    # -----------------------------------------------------------------------
    def extract_weighing_matrix(self, session: Any) -> List[DeliberationTopic]:
        """
        Dissects transcript to extract choices, pro/con arguments, and verdict consensus.
        """
        title, segments, explicit_decisions, _ = self._extract_session_data(session)
        if not segments and not explicit_decisions:
            return []

        all_sentences = []
        for s in segments:
            text = s.get("text", "")
            sents = [sent.strip() for sent in re.split(r'(?<=[.!?])\s+', text) if len(sent.strip()) > 8]
            all_sentences.extend(sents)

        topics: List[DeliberationTopic] = []
        current_topic_name = "Core Architectural & Directional Choice"
        pros: List[str] = []
        cons: List[str] = []
        has_decision = bool(explicit_decisions)

        if explicit_decisions:
            for d in explicit_decisions:
                pros.append(f"Decided: {d}")

        re_pro = re.compile("|".join(PRO_PATTERNS), re.IGNORECASE)
        re_con = re.compile("|".join(CON_PATTERNS), re.IGNORECASE)
        re_decide = re.compile(r"\b(we decided|we agreed|settled on|chosen|selected|consensus)\b", re.IGNORECASE)

        for sent in all_sentences:
            # Topic indicator (e.g. "evaluating X versus Y")
            m_eval = re.search(r"\bevaluat\w+\s+([\w\s]+versus[\w\s]+)", sent, re.IGNORECASE)
            if m_eval:
                current_topic_name = f"Evaluation: {m_eval.group(1).strip()}"

            if re_decide.search(sent):
                has_decision = True
                pros.append(sent)
            elif re_pro.search(sent):
                pros.append(sent)
            elif re_con.search(sent):
                cons.append(sent)

        status = "CONSENSUS_REACHED" if has_decision else ("OPEN_DEBATE" if (pros and cons) else "TABLED")

        # Deduplicate
        pros_clean = list(dict.fromkeys(pros))[:5]
        cons_clean = list(dict.fromkeys(cons))[:5]

        if pros_clean or cons_clean:
            topics.append(DeliberationTopic(
                topic=current_topic_name,
                pros_agreements=pros_clean,
                cons_concerns=cons_clean,
                status=status
            ))

        return topics

    # Alias for sovereign agentic deliberation
    weigh_decisions = extract_weighing_matrix

    # -----------------------------------------------------------------------
    # 3. Risk & Blocker Radar
    # -----------------------------------------------------------------------
    def extract_risk_radar(self, session: Any) -> List[RiskItem]:
        """
        Scans statements for technical, operational, and compliance risks.
        """
        _, segments, _, _ = self._extract_session_data(session)
        if not segments:
            return []

        risks: List[RiskItem] = []
        re_high = re.compile("|".join(RISK_HIGH_PATTERNS), re.IGNORECASE)
        re_med = re.compile("|".join(RISK_MEDIUM_PATTERNS), re.IGNORECASE)

        for s in segments:
            text = s.get("text", "")
            sentences = [sent.strip() for sent in re.split(r'(?<=[.!?])\s+', text) if len(sent.strip()) > 8]
            for sent in sentences:
                if re_high.search(sent):
                    hint = "Action required: Perform security review and pin verified dependencies."
                    risks.append(RiskItem(text=sent, severity="HIGH", mitigation_hint=hint))
                elif re_med.search(sent):
                    hint = "Monitor metrics and evaluate optimization fallback."
                    risks.append(RiskItem(text=sent, severity="MEDIUM", mitigation_hint=hint))

        # Deduplicate by text
        seen = set()
        deduped = []
        for r in risks:
            if r.text not in seen:
                seen.add(r.text)
                deduped.append(r)

        return deduped

    # Alias for risk detector
    detect_risks_and_blockers = extract_risk_radar

    # -----------------------------------------------------------------------
    # 4. Agentic Action Dispatcher (Follow-Up Email & Task Cards)
    # -----------------------------------------------------------------------
    def generate_followup_email(self, session: Any, attendees: Optional[List[str]] = None) -> str:
        """
        Generates a polished, professional meeting follow-up email draft.
        """
        title, segments, decisions, actions = self._extract_session_data(session)
        date_str = datetime.now().strftime("%B %d, %Y")
        attendees_str = ", ".join(attendees) if attendees else "Team"

        if not decisions and segments:
            from engine.meeting_notetaker import DECISION_PATTERNS
            decision_regex = re.compile("|".join(DECISION_PATTERNS), re.IGNORECASE)
            for seg in segments:
                txt = seg.get("text", "")
                if decision_regex.search(txt) and txt not in decisions:
                    decisions.append(txt)

        if not actions and segments:
            from engine.meeting_notetaker import ACTION_ITEM_PATTERNS
            action_regex = re.compile("|".join(ACTION_ITEM_PATTERNS), re.IGNORECASE)
            for seg in segments:
                txt = seg.get("text", "")
                if action_regex.search(txt) and txt not in actions:
                    actions.append(txt)

        dec_lines = "\n".join(f"  • {d}" for d in decisions) if decisions else "  • No formal decisions recorded."
        act_lines = "\n".join(f"  [ ] {str(a)}" for a in actions) if actions else "  [ ] No open action items."

        email_draft = f"""Subject: Meeting Recap: {title} ({date_str})

Hi {attendees_str},

Here is the concise executive recap from our discussion today:

## 📌 Executive Summary
Recap of decisions, discussion points, and next steps recorded for {title}.

## 🎯 Key Decisions Made
{dec_lines}

## ✅ Action Items & Commitments
{act_lines}

Please review your respective action items and reply if any context needs clarification.

Best regards,
FlowPilot Local Voice Assistant
"""
        return email_draft

    # Alias for drafting email
    draft_followup_email = generate_followup_email

    def generate_task_cards(self, session: Any) -> List[TaskCard]:
        """
        Generates GitHub / Jira formatted Markdown task cards from action items.
        """
        title, segments, _, actions = self._extract_session_data(session)

        if not actions and segments:
            from engine.meeting_notetaker import ACTION_ITEM_PATTERNS
            action_regex = re.compile("|".join(ACTION_ITEM_PATTERNS), re.IGNORECASE)
            for seg in segments:
                txt = seg.get("text", "")
                if action_regex.search(txt) and txt not in actions:
                    actions.append(txt)

        cards = []

        for idx, act in enumerate(actions, 1):
            act_text = str(act).strip()
            # Determine priority heuristic
            priority = "High" if any(w in act_text.lower() for w in ["critical", "security", "immediately", "blocker", "must"]) else "Medium"
            card_title = f"Task: {act_text[:60]}..." if len(act_text) > 60 else f"Task: {act_text}"

            body = f"""### 📋 {card_title}
- **Source Meeting:** {title}
- **Assigned Action:** {act_text}
- **Priority:** {priority}
- **Status:** To Do
- **Origin Date:** {datetime.now().strftime('%Y-%m-%d')}

#### Acceptance Criteria:
- [ ] Task executed and verified against requirements.
- [ ] Documentation updated if relevant.
"""
            cards.append(TaskCard(
                title=card_title,
                markdown_body=body,
                priority=priority
            ))

        return cards
