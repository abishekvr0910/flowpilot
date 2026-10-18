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

The runtime model loader uses local-only weights. Provision required `tiny` and `base` model files during the build/setup phase on a connected machine, then validate offline behavior separately. The [CI workflow](../../.github/workflows/ci.yml) shows its current model provisioning step.

## Verify before packaging

```powershell
python -X utf8 tests/run_all_tests.py
npm test
```

The runner currently defines 37 suites. Physical microphone and audio-ducking checks may be skipped in headless CI; a skip is not a pass for that hardware. Require a green [GitHub Actions run](https://github.com/abishekvr0910/flowpilot/actions/workflows/ci.yml) for the intended commit and perform explicit Windows hardware checks before release. If CI is red, stop and investigate; do not reuse results from an older tag.

## Build and inspect

```powershell
python -m PyInstaller flowpilot.spec --noconfirm
python -X utf8 tests/test_standalone_binary_smoke.py
```

Inspect the complete `dist/FlowPilot/` directory, not just `FlowPilot.exe`: model assets, Qt plugins, native libraries, notices, startup, microphone access, focus behavior, single-instance lifecycle, and clean exit. Test on a clean Windows machine or disposable VM with the intended audio hardware.

## Publish only after review

Record the source commit, artifact size, SHA-256 hash, test results, skipped hardware checks, and known limitations in a release-specific manifest. Review bundled third-party notices using [THIRD_PARTY_LICENSES.md](../../THIRD_PARTY_LICENSES.md). Publish an immutable versioned ZIP through GitHub Releases only after the exact candidate build has passed the required checks. The [current release manifest](RELEASE_ARTIFACT_MANIFEST.md) documents v3.0.2, not an unpublished v3.1.0 artifact.
