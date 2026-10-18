# Gemini review request: FlowPilot Companion Studio

> **Historical snapshot - superseded.** Retained for provenance only. Do not use this document as current instructions, test status, performance proof, legal/compliance advice, or up-to-date competitor information. See the [archive index](README.md) for current sources.

Review the attached `COMPANION_STUDIO_PLAN.md` as a senior desktop engineer and product designer. Return your critique in text. This is design review only: do not edit code, run tools, inspect the filesystem, start applications, send messages, or delegate to other agents. The provided document is the complete review input.

The user wants a dependable kitty companion, a real customization window, their own emoji and small animated creations, and a Hermes-inspired system that adapts to their preferences. Keep the result small enough to build and enjoyable enough to use.

Constraints: Python/PySide6/QPainter, one desktop process/event loop, local CPU dictation, no runtime cloud egress, no passive focus theft, no semantic corruption, bounded resource use. The user has authorized a separate Gemini design review, not cloud features inside FlowPilot. The existing baseline has unresolved test failures; do not assume a green build.

Please return, in at most 1,500 words:

1. The five highest-impact problems in the proposal, ranked by severity and tied to sections.
2. Concrete improvements to the interaction design, including exact single/double-click and Studio focus behavior.
3. A realistic asset/animation resource strategy and any failure in the proposed limits.
4. A useful local learning loop with transparent approval, conflict resolution, forgetting, and no transcript surveillance.
5. Missing state transitions, data fields, privacy cases, or tests that would block implementation.
6. A revised first implementation slice, with acceptance criteria, and what to defer.
7. Explicit disagreements with the plan and reasons; no invented benchmark results or claims that you ran tests.

Treat the broad directive's focus and memory requirements as unresolved design decisions where noted. Recommend precise wording or an alternative; do not silently waive them. Prefer improving the existing architecture over adding servers, model frameworks, autonomous tools, or a second desktop runtime.
