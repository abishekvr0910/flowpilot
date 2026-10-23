# FlowPilot Pilot Quickstart

**Scope:** A fixed candidate provided by the maintainer, or the exact source revision being evaluated. Record its identity before testing. The [artifact manifest](../release/RELEASE_ARTIFACT_MANIFEST.md) retains the old RC2 archive and hashes for reference. That archive does not include later source repairs. A repaired candidate needs its own review, validation, and hashes before distribution.

## Before you start

- Use a Windows 10 or 11 machine with a functioning microphone.
- Read [PRIVACY.md](../../PRIVACY.md):
  - **Fresh profiles default to `save_history_text: false`**: no dictation audio, transcripts, or insights are written to disk.
  - Existing user profiles retain their previously saved choice.
  - The most recent dictation remains in a process memory recovery buffer until replaced or the app exits. Windows clipboard history and the destination app have separate behavior.
  - Turning history off prevents new writes but does not delete older vault files.
  - Meetings, scratchpad documents, and diagnostic logs have independent lifecycles.
- Use non-sensitive test phrases initially. Do not dictate employer-confidential, medical, or credential data during pilot testing.

## Testing options

### Option A: Packaged candidate binary (Recommended for pilots)

1. Obtain the candidate ZIP and its matching reviewed manifest. Record the filename, source identity, SHA-256, and signing status. If a repaired candidate has not been provided, this step remains pending.
2. Compute the archive SHA-256 with `Get-FileHash -Algorithm SHA256 -LiteralPath <candidate-zip-path>` and compare it with that candidate's manifest.
3. Extract the archive, open its `FlowPilot` directory, and run `FlowPilot.exe`. The manifest must identify its bundled models and offline test evidence. Do not reuse RC2 hashes for different bytes.

### Option B: Run from source checkout

```powershell
git clone https://github.com/abishekvr0910/flowpilot.git
cd flowpilot
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python desktop_app.py
```

Record `git rev-parse HEAD` and whether local changes are present. Provision local model weights using the [source setup instructions](../../QUICKSTART.md#running-current-source) before offline testing. Source results do not verify an older ZIP.

## First dictation

1. Open Notepad (or your preferred editor) and click inside the text area.
2. Use the dictation shortcut shown in Settings (initially `Ctrl+Shift+Space` in toggle mode), speak a short non-sensitive phrase, then press it again to finish. You can switch to `F9` and push-to-talk mode in Settings.
3. Check the inserted text and whether focus remained in Notepad. Record the actual stop-to-text time.
4. Select a companion through its right-click **Appearance Style** menu or Companion Studio.
5. If text does not paste, use the tray's **Copy Last Dictation** action. Check [known issues](../testing/flowpilot_known_issues.md) for elevated-window and focus limitations.
6. In current repaired source, external transform Replace and Revert are unavailable because document and selection changes cannot be verified. Use the transform preview and Copy Output, then paste manually. Scratchpad voice editing uses separate guarded transactions.

## Report results

Use the [pilot checklist](PILOT_TESTING_CHECKLIST.md) and [bug template](PILOT_BUG_REPORT_TEMPLATE.md).
Record outcomes separately:

- **Verified paste**: Text confirmed in target buffer.
- **Unverified dispatch**: Keystrokes sent to verified focus, but target buffer was unreadable.
- **Safe refusal**: Window focus lost or elevation mismatch; text preserved in recovery buffer without typing into wrong window.
- **Recovery used**: User copied from in-memory recovery buffer via tray or shortcut.
- **Duplicate insertion**: Any repeated or phantom keystrokes observed.

Inspect and redact any logs or screenshots before sharing.
