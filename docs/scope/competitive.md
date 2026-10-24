# Competitive validation

The goal is a measurable advantage for Windows developer dictation with local processing. A feature count, a green test suite, or a pleasant companion cannot establish that advantage alone.

## Next release evidence

### 29. Competitive outcome evaluation · in-progress · GA

Compare FlowPilot and Wispr Flow on the same speech and target tasks. Measure time to correct, usable text, factual accuracy, delivery, resource use, setup effort, and preference. Keep offline capability separate from normal connected performance.

**Done when:** a frozen protocol, exact versions, consented corpus, independent target observations, raw outcomes, and uncertainty support a dated, narrowly worded conclusion. Losses and inconclusive categories remain visible. The evaluation can finish without producing a superiority claim.

- [x] Design it (spec): [spec 0003](../specs/0003-visible-delivery-benchmark-observer.md)
- [x] Implement independent target document observer: `benchmarks/delivery_observer.py`
- [x] Protect against false positives (deletions, stray edits, typing dwell): `tests/test_delivery_observer.py` (17 tests passed on 24 October 2026)
- [ ] Execute paired head-to-head live trials with consented speech corpus (Feature 15) and record outcome ledger.

Build on the [existing comparison protocol](../testing/WISPR_FLOW_HEAD_TO_HEAD.md), [runtime protocol](../testing/RUNTIME_PERFORMANCE_PROTOCOL.md), and [real voice schema](../evaluation/REAL_VOICE_CORPUS_SCHEMA.md). The [complete Gemini handoff](../handoffs/GEMINI_PRODUCT_COMPLETION_AND_COMPETITIVE_VALIDATION.md) provides proposed thresholds, corpus stages, task coverage, and claim rules. Its proposals need to be frozen before final evaluation; they are not measured results.

The language corpus, insertion safety, and runtime tools remain owned by scope features 15, 16, and 25. This feature owns comparison design and the resulting competitive decision, avoiding duplicate measurement engines.

## Boundaries

The first claim is limited to tested Windows developer workflows, languages, models, machines, and app versions. Mobile keyboards, cloud collaboration, broad autonomous actions, and regulated use are outside this release. External voice editing remains a later feature under 22. Original companions remain under 10, 20, 21, and 27.

"100% better than Wispr Flow" has no defined denominator or finite acceptance test. A defensible claim names the measured outcome and its limits, such as less correction time on a stated Windows developer corpus. Do not substitute "100% of planned checks completed" for "100% better."
