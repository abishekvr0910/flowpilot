# FlowPilot Pilot Quickstart

**Scope:** The current pilot prerelease candidate is **v3.1.0-RC8** (`FlowPilot-v3.1.0-RC8-win64.zip`, SHA-256 `2DFB83BCC98068389E6962FCC7A0A25131C90F7D546B8CD3ABDBC6E54A43F69F`). Record its identity before testing. See the [artifact manifest](../release/RELEASE_ARTIFACT_MANIFEST.md) for full candidate evidence and SHA-256 digests. RC8 is an unsigned pilot prerelease for controlled testing, not a general release.

## Before you start

- Use a Windows 10 or 11 machine with a functioning microphone.
- Read [PRIVACY.md](../../PRIVACY.md):
  - **Fresh profiles default to `save_history_text: false`**: no dictation audio, transcripts, or insights are written to disk.
  - Existing user profiles retain their previously saved choice.
  - The most recent dictation remains in a process memory recovery buffer until replaced or the app exits. Windows clipboard history and the destination app have separate behavior.
  - Turning history off prevents new writes but does not delete older vault files.
  - Meetings, scratchpad documents, and diagnostic logs have independent lifecycles.
- Use non-sensitive test phrases initially. Do not dictate employer-confidential, medical, or credential data during pilot testing.
- Note on Indic languages: Hindi, Tamil, and Malayalam are strictly experimental in RC8 due to high error rates on natural human speech.

## Testing options

### Option A: Packaged candidate binary (Recommended for pilots)

1. Obtain `FlowPilot-v3.1.0-RC8-win64.zip` from the [v3.1.0-RC8 prerelease](https://github.com/abishekvr0910/flowpilot/releases/tag/v3.1.0-RC8).
2. Compute the archive SHA-256:
   ```powershell
   Get-FileHash -Algorithm SHA256 -LiteralPath .\FlowPilot-v3.1.0-RC8-win64.zip
   # Expected: 2DFB83BCC98068389E6962FCC7A0A25131C90F7D546B8CD3ABDBC6E54A43F69F
   ```
3. Extract the archive, open the `FlowPilot` folder, and launch `FlowPilot.exe`. (Windows SmartScreen may prompt because the pilot build is unsigned; click *More info* -> *Run anyway* if proceeding).

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
