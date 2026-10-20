# FlowPilot FAQ

**Scope:** Current `master` pilot source. The published [v3.0.2 Windows release](https://github.com/abishekvr0910/flowpilot/releases/tag/v3.0.2-release) has a different feature set. This FAQ is not a purchasing offer or compliance certification.

## Is speech recognition local?

Yes. The current STT engine uses the local `faster-whisper` model and rejects cloud transcription mode. The [network egress regression test](../../tests/test_network_egress.py) covers selected code paths; it is not an independent audit of every configuration. Optional integrations should be evaluated separately.

## Does FlowPilot store audio or transcripts?

Not by default for new dictations in current `master`: `save_history_text: false` bypasses the History Vault and keeps the latest dictation only in memory for recovery. Opting into history saves transcripts and WAV recordings locally. Previously saved entries remain until deleted, and meeting notes are stored separately when that feature is used. See [PRIVACY.md](../../PRIVACY.md) for paths and deletion behavior.

## Is it certified for HIPAA or GDPR use?

No certification or legal suitability determination is claimed. Local processing can reduce some third-party data transfers, but deployment suitability depends on retention, device security, access controls, organizational policy, and legal review.

## Do I need a GPU?

No for the default CPU INT8 model. Speed and memory usage vary by processor, model, microphone, and dictation length. The [v3.0.2 evaluation](../release/FLOWPILOT_V302_RELEASE_REPORT.md) describes one dated test host; its results are not guarantees for current source or other devices.

## Which shortcuts are available?

The initial dictation shortcut is `Ctrl+Shift+Space` in toggle mode. Existing profiles retain `F9` and `Ctrl+Alt+Space` as aliases until a shortcut is explicitly saved in Settings. You can choose `F9` (or another available key) and set toggle or push-to-talk there. FlowPilot blocks its own recovery and transforms shortcuts from being reused for dictation; Windows or other applications can still reserve keys. Use the companion's right-click menu or Companion Studio to select an appearance; double-click does not cycle styles in current source.

## What if text fails to paste?

The tray's **Copy Last Dictation** action can recover the most recent in-memory result. FlowPilot attempts to restore clipboard contents after insertion and checks the clipboard sequence to avoid overwriting a newer user copy. Target applications and clipboard formats may differ; report reproducible failures.

## What is FactGuard?

It is a deterministic formatting guard designed to preserve numbers, dates, negations, and developer identifiers. It does not guarantee error-free speech recognition or replace review of important text.

## Is there a paid plan or refund policy?

The source code is [MIT-licensed](../../LICENSE). The [GitHub Releases page](https://github.com/abishekvr0910/flowpilot/releases) lists published downloads. No paid plan or refund policy is offered through this repository. Use [GitHub Issues](https://github.com/abishekvr0910/flowpilot/issues) for non-sensitive support and [SECURITY.md](../../SECURITY.md) for vulnerability reports.
