# Build and Release Guide (Windows)

This guide describes **building current source**, not the already published v3.0.2 ZIP. Do not publish or label a new release solely because a local executable launches.

## Prepare the environment

Use Windows 10/11, Python 3.11 or newer, and a supported microphone. Clone the repository into a path of your choice:

```powershell
git clone https://github.com/abishekvr0910/flowpilot.git
cd flowpilot
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e ".[dev,web]"
```

The runtime model loader uses local-only weights. Provision the `base` and `small` model files bundled by the current RC4 spec during the build/setup phase on a connected machine, then validate offline behavior separately. The [CI workflow](../../.github/workflows/ci.yml) shows its current model provisioning step.

## Build the candidate, then verify it

Record the candidate commit and worktree state first. A distributable release must identify all included source changes; a dirty worktree is a development candidate, not evidence of a reproducible tag build.

Build before running the regression gate because the gate includes packaged-binary checks. Otherwise those checks can accidentally test an older executable.

```powershell
python -m PyInstaller flowpilot.spec --noconfirm
python -X utf8 tests/run_all_tests.py
npm test
```

The runner currently defines 56 suites (2026-10-24). Use `python -X utf8 tests/run_all_tests.py --require-all` for release verification. Physical microphone, audio-ducking, clipboard-sequence, and real-editor insertion checks may be skipped in hosted headless CI; a skip is not a pass for those behaviors. Require a green [GitHub Actions run](https://github.com/abishekvr0910/flowpilot/actions/workflows/ci.yml) for the intended commit and perform explicit interactive Windows hardware and insertion checks before release. If CI is red, stop and investigate; do not reuse results from an older tag.

## Inspect the exact artifact

```powershell
Get-AuthenticodeSignature -LiteralPath .\dist\FlowPilot\FlowPilot.exe |
    Select-Object Status, StatusMessage, SignerCertificate
Get-FileHash -Algorithm SHA256 -LiteralPath .\dist\FlowPilot\FlowPilot.exe
```

Inspect the complete `dist/FlowPilot/` directory, not just `FlowPilot.exe`: model assets, Qt plugins, native libraries, notices, startup, microphone access, focus behavior, single-instance lifecycle, and clean exit. Test on a clean Windows machine or disposable VM with the intended audio hardware.

`NotSigned` means there is no Authenticode publisher signature. A local build inspected on October 18, 2026 had that result; it does not establish the signature state of other artifacts. For a signed release, verify the expected publisher identity and signature status after signing, then smoke-test that exact candidate. A self-signed test certificate does not establish public publisher trust. Do not ask users to disable SmartScreen or antivirus.

Create the final ZIP only after candidate verification. Compute its SHA-256 after its contents are final and include that hash in the matching release record. Signing or rebuilding afterward changes artifact identity and requires updated evidence. A checksum is not a malware assessment or proof that a binary corresponds to reviewed source. See Microsoft's [Get-AuthenticodeSignature reference](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.security/get-authenticodesignature).

## Evidence required for a public candidate

Use [RELEASE_EVIDENCE_TEMPLATE.md](RELEASE_EVIDENCE_TEMPLATE.md) for each candidate. Require:

- The source commit, dependency/model versions, build command/toolchain, final ZIP hash, executable hash, and explicit signing status.
- CI results for that commit, plus separate interactive Windows measurements. Report first-attempt insertion, recovery, duplicates, safe refusals, and untested targets separately. Non-interactive rejection tests cannot establish editor compatibility.
- A clean-profile first run, model provisioning, microphone selection, normal-user execution, recovery, quit/relaunch, and upgrade from an existing profile. Confirm opt-in/history settings survive the upgrade as documented.
- Privacy checks for each feature being advertised: history on/off, older-record retention/deletion, meeting notes, scratchpad, logs, optional API, and optional local LLM integration. Do not extend a desktop dictation test result to API multipart uploads without testing that path.
- A dependency and model inventory from the built bundle, with applicable license/NOTICE files. Include art assets as well as code dependencies.
- Release-specific limitations and recovery instructions. Record the previous download for rollback; do not promise downgrade-compatible profile files without testing them.

Before marketing broader security assurance, verify the optional API's token and WebSocket origin checks in the exact release, add request limits, minimize window-title diagnostics, and define which clipboard formats are supported. Track each as a real engineering issue with verification; documentation alone does not implement these controls. Public support follows [SUPPORT.md](../../SUPPORT.md); private security reports follow [SECURITY.md](../../SECURITY.md).

## Publish only after review

Record the source commit, artifact size, SHA-256 hash, test results, skipped hardware checks, and known limitations in a release-specific manifest. Review bundled third-party notices using [THIRD_PARTY_LICENSES.md](../../THIRD_PARTY_LICENSES.md). Publish a versioned ZIP through GitHub Releases only after the exact candidate build has passed the required checks. Do not replace a reviewed asset with different bytes under the same version. Verify GitHub tag/release protection settings before describing assets as immutable. The [current release manifest](RELEASE_ARTIFACT_MANIFEST.md) distinguishes the historical published v3.0.2 release from the current RC4 pilot candidate and older candidates.
