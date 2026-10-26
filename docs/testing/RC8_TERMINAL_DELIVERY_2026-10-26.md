# RC8 Windows delivery check, 26 October 2026

**Source:** commit `b48128c`, built locally with PyInstaller 6.22.3 and Python 3.11.15 on Windows 11. The build is unsigned. This is a pilot verification record, not a measured 99.9% reliability claim.

The interactive desktop was available and idle during physical insertion tests. The strict audit runner on the new `dist/FlowPilot/FlowPilot.exe` reported **59 passed, 0 skipped, 0 failed** in 136.69 seconds. Its five physical desktop paths included real microphone capture, Notepad buffer checks, and cross-app insertion. The packaged binary passed its named mutex and asset smoke test. `FlowPilot.exe --self-test` loaded bundled base weights with an empty isolated Hugging Face cache, transcribed the SAPI phrase, exited 0, and left the cache empty. `npm test` passed the loopback REST and WebSocket lifecycle.

An additional ten sequential runs of `tests/test_cross_app_injection.py` each exited 0. The raw ignored log is `scratch/rc8-cross-app-trials.txt`. All ten runs recorded the test's final physical confirmation marker for each of these targets:

| Target | Final document evidence | Confirmed runs |
|---|---|---:|
| Windows 11 Notepad | Text read from the owned document buffer | 10/10 |
| Command Prompt hosted by Windows Terminal | Unique command output token read from a private test file | 10/10 |
| PySide6 editor | Text read from `QTextEdit.toPlainText()` | 10/10 |

This test confirms final delivery in those isolated test windows. It does not measure first-attempt insertion separately for every target, browser editors, Word, Slack, focus changes during a long paste, different integrity levels, remote desktops, or other machines. No duplicate insertion was observed in these ten final buffers, but the sample is too small for a reliability percentage claim. General release still needs a wider pilot matrix.

The reproduced failure before the fix was specific: Windows Terminal's `CASCADIA_HOSTING_WINDOW_CLASS` accepted the synthesized `Shift+Insert` events without delivering the clipboard text into Command Prompt. Direct Unicode `SendInput` delivered the same text on this machine. The new route is limited to verified `ConsoleWindowClass` and `CASCADIA_HOSTING_WINDOW_CLASS` targets, refuses newline-containing text, leaves the clipboard untouched, and reports dispatch as `SENT_UNVERIFIED` unless a caller independently verifies target content. Focus and target-integrity checks run before dispatch. A partially dispatched or uncertain result is not retried automatically.

The original strict run after the UI warning change reported 58 passed and one failed wording assertion in `test_pilot_reliability.py`; it was corrected to check the new experimental warning and amber style. The subsequent exact-build strict run above passed 59/59. Both outcomes are kept in this record.
