# Release evidence template

Copy this template into a version-specific release record. Every field starts **pending**; replace it with evidence for the exact candidate. This template is not a release approval.

| Identity | Value |
| --- | --- |
| Version/tag and source commit | Pending |
| Worktree clean / included patch identity | Pending |
| Build date, Windows version, Python/PyInstaller version | Pending |
| Dependency and model inventory, model revisions/hashes | Pending |
| Final ZIP filename, size, SHA-256 | Pending |
| Executable SHA-256 | Pending |
| Authenticode status and publisher | Pending |
| CI run URL for this commit | Pending |
| Human review and release owner | Pending |

## Verification

| Check | Result and evidence |
| --- | --- |
| Full regression: passed / failed / skipped | Pending |
| Exact packaged candidate smoke test | Pending |
| Clean Windows profile: setup, microphone, model, first dictation | Pending |
| Interactive insertion by app/version: attempts, first successes, recoveries, duplicates, safe refusals | Pending |
| Stop-to-visible-text timing: definition, sample count, p50/p95, failures | Pending |
| History off/on, existing entries, meeting/scratchpad retention | Pending |
| Network paths and optional integrations tested | Pending |
| Diagnostic content reviewed with synthetic canaries | Pending |
| Bundled code, model, and art notices verified | Pending |
| Upgrade, quit/restart, and rollback limitations | Pending |

## Notes for users

- New behavior and fixes: Pending.
- Known limitations and untested configurations: Pending.
- Model download/provisioning requirements: Pending.
- Local data migration or retention changes: Pending.
- Signature status and download verification: Pending.
- Recovery and support: link to the version-appropriate instructions.

Do not turn pending fields into passes, reuse an older build's measurements, or describe a safe refusal as a successful paste. When source or packaged bytes change, re-evaluate the affected checks and update artifact identity.
