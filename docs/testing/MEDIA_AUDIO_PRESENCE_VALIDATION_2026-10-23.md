# Media audio presence validation, 23 October 2026

This is the release gate record for the companion media feature and the
dashboard screen fit repair made after source commit `7db96df`. It records
what was seen on the live Windows desktop. The audio meter detects audible
playback. It cannot identify a video, browser tab, or page content.

## Behavior and earlier engineering checks

The Windows render session meter runs in a background sampler. Qt reads only
the cached result, so slow COM audio queries cannot block the visibility tick.
The controller ignores muted sessions and requires sustained audio before
hiding the companion. After 1.5 seconds of quiet it resets the latch, so a
new sound must sustain again. It reads no pixels, titles, URLs, clipboard, or
transcript. Microsoft documents [session mute state](https://learn.microsoft.com/en-us/windows/win32/api/audioclient/nf-audioclient-isimpleaudiovolume-getmute)
and [peak meters](https://learn.microsoft.com/en-us/windows/win32/api/endpointvolume/nn-endpointvolume-iaudiometerinformation)
as separate signals.

Before the live gate, `tests/test_companion_visibility.py` passed 22 focused
tests with fake audio samples and COM objects. Five direct audio reads took
137.56 ms on first call and 26.68 to 29.31 ms thereafter; 1,000 cached reads
had a maximum of 0.0685 ms. An earlier non strict 54 suite run reported 49
passed, 5 skipped, 0 failed in a headless session. Those checks did not prove
live browser or presentation behavior.

## Exact packaged build under test

The following five checks ran on the unlocked Windows input desktop using one
isolated PyInstaller executable from the repaired source tree:

| Item | Evidence |
|---|---|
| Executable | `scratch/release-live-fixtures-20261023/rc3-dist/FlowPilot/FlowPilot.exe` |
| Size | 24,885,089 bytes |
| SHA-256 | `D17FEC1C94918520CAF51B3F250897875671B6BB0B401429315AA08999ABF52E` |
| Runtime | Separate config profile and named mutex, bundled Whisper base and small models, Silero VAD assets |
| Media fixture | Local 15 second H.264/AAC file played in a normal Edge window |

An existing Chrome audio session interfered with the first controlled Chrome
attempt. Muting that process also muted the Chrome fixture, so that attempt
was discarded. The session was restored. For the final controlled media and
presentation trials, the existing Chrome session was temporarily muted while
an independent Edge fixture played, then restored immediately afterward.
This avoids counting another application's sound as the fixture.

## Five live checks

| Check | Direct observation | Result |
|---|---|---|
| Audible windowed video | Edge playback hid the HUD in 2.141 s; unmuting hid it again in 1.414 s | Pass as an audio presence heuristic |
| Muted or paused video | Muting restored the HUD in 2.068 s; pausing restored it in 1.717 s | Pass |
| Browser F11 fullscreen | Edge held foreground; F11 hid the HUD in 0.556 s with fullscreen classification and Windows shell state 2. F11 exit restored it in 0.706 s | Pass |
| Presentation | A real PowerPoint slide show held foreground and covered the primary monitor. It hid the HUD in 0.607 s and restored it in 0.746 s after exit | Pass |
| F9 while hidden | With persistent Hide selected, F9 dictated a local WAV into a unique Notepad document. The buffer contained `FlowPilot hidden companion dictation test.` once. Notepad held foreground and the HUD remained hidden before, during, and after recording | Pass on repeat with stable focus |

The first hidden F9 attempt failed because Chrome took foreground during the
trial; the expected phrase was absent from the inspected Notepad document.
It was not counted as an insertion success. When the desktop was left idle,
the repeat kept Notepad focus and verified the phrase. PortAudio device
numbers also changed between runs. The passing trial checked the actual
`CABLE Output` input and `CABLE Input` playback endpoints first.

## Physical layout gate and repair

The initial build from `7db96df` exposed a layout defect on the 125 percent
primary display: the dashboard bottom actions fell below the taskbar. The
repair bounds the native window frame to the usable monitor area and enables
a Home scrollbar when content extends below the viewport. Two focused
regression tests now cover those conditions.

On the repaired packaged build the dashboard frame `[226, 41, 1694, 988]`
fit inside the primary work area `[0, 0, 1920, 1020]`. After moving to the
100 percent secondary monitor, frame `[1970, 13, 3144, 716]` fit work area
`[1920, 0, 3286, 720]`; it still fit after returning to the primary. A
native Qt capture on each display showed the Studio Cancel and Apply Changes
buttons inside the frame. A direct screenshot on the secondary display was
occluded by another fullscreen application and was discarded. The packaged
secondary result is therefore a frame geometry check, not a screenshot claim.

## Automated and standalone gates

`python -X utf8 tests/run_all_tests.py --require-all`, with
`FLOWPILOT_TEST_EXE` set to the exact executable above, completed in 175.07 s:
**54 passed, 0 skipped, 0 failed**. This included physical Notepad and cross
application insertion, the 18 scenario desktop suite, and packaged smoke.
The same binary passed a separate offline self test with an isolated empty
model cache and transcribed the SAPI fixture. `npm test` passed local REST and
WebSocket integration on loopback port 8766.

## Remaining limits

Audible background music can also hide the companion, and muted windowed
video does not. Per app rules remain the precise user control. Other checks
in spec 0001, including Studio app rule editing, restart persistence,
reduced motion, and a wider pilot across target apps, remain separate from
these five release checks. This gate does not establish universal paste
reliability or real speaker accuracy. The build is unsigned. RC2 hashes are
historical; a new candidate needs its own manifest and hosted CI result.
