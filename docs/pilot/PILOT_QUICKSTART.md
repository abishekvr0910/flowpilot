# FlowPilot Pilot Quickstart

**Scope:** Current `master` source checkout. The only published download is the older [v3.0.2 Windows release](https://github.com/abishekvr0910/flowpilot/releases/tag/v3.0.2-release); do not use its ZIP as evidence that current pilot features are packaged.

## Before you start

- Use Windows 10 or 11 with a working microphone and Python 3.11 or newer.
- Read [PRIVACY.md](../../PRIVACY.md): current source saves completed dictation transcripts and WAV audio locally by default.
- Use non-sensitive test phrases. Do not put client, patient, or employer-confidential speech into a pilot build without approval from the relevant organization.

## Run from source

```powershell
git clone https://github.com/abishekvr0910/flowpilot.git
cd flowpilot
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python desktop_app.py
```

Speech model weights must already be cached locally. If they are missing, the local loader reports an error instead of downloading them at runtime. Follow the model setup guidance in the repository before testing offline.

## First dictation

1. Open Notepad and click inside a document.
2. Use the dictation shortcut shown in Settings (initially `Ctrl+Shift+Space` in toggle mode), speak a short non-sensitive phrase, then press it again to finish. You can choose `F9` and switch to push-to-talk in Settings; existing profiles also retain the former `F9` alias until a shortcut is explicitly saved.
3. Check the inserted text and whether focus remained in Notepad. Record the actual stop-to-text time; do not assume a fixed latency.
4. Select a companion through its right-click **Appearance Style** menu or Companion Studio. Double-click does not cycle styles in current source.
5. If text does not paste, use the tray's **Copy Last Dictation** action. Check [known issues](../testing/flowpilot_known_issues.md) for elevated-window and hotkey limitations.

## Report results

Use the [pilot checklist](PILOT_TESTING_CHECKLIST.md) and [bug template](PILOT_BUG_REPORT_TEMPLATE.md). Inspect and redact any logs or screenshots before sharing. Check the [live CI status](https://github.com/abishekvr0910/flowpilot/actions/workflows/ci.yml) separately; a local pilot session is not a substitute for a passing regression gate.
