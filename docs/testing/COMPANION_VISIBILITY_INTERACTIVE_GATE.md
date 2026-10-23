# Companion visibility interactive gate

The companion visibility code is newer than RC2. The five packaged build checks
for media, F11, PowerPoint, hidden F9, and physical layout are recorded in
[the media validation note](MEDIA_AUDIO_PRESENCE_VALIDATION_2026-10-23.md).
Other rows below remain separate checks for the wider spec 0001 review.
Automated policy tests alone cannot prove how editors, the tray, and display
transitions behave together on a real desktop.

Use a fresh test profile and a distinct single instance mutex. The verified
package is now `dist/FlowPilot/FlowPilot.exe`; its hash is in the media
validation note and the RC3 manifest. Keep the RC2 archive unchanged. If
another FlowPilot instance owns F9, close that exact process normally before
testing. Do not terminate processes by generic name.

| Check | Action | Pass condition |
|---|---|---|
| Smart fullscreen | Choose Smart. In Chrome play a video and press F11. Then press F11 again. | Pet disappears and returns within one second of each transition, with no focus theft or flashing. |
| Windows presentation | Turn on Windows presentation mode or start a full screen slide show. | Pet hides; tray remains available; it restores when presentation ends. |
| Maximized editor | Maximize VS Code without entering fullscreen. | Pet uses quiet edge, not Hidden. F9 still dictates into the editor. |
| Multi monitor | Leave a video fullscreen on a secondary display, then work in an editor on the primary display. | Record whether the policy hides the pet globally as documented. No unexpected show over the video. |
| Manual choice | Select Hide, restart FlowPilot, then choose Show companion from the tray. Repeat with Always show. | Choice survives restart; the selected character and position do not change. |
| App rule | Set `code.exe` to Normal and then Hidden in Studio; remove the rule. | Rule wins over quiet default when not fullscreen; removal returns to default without changing the character. |
| Hidden dictation | Hide pet, press F9, dictate to Notepad, and inspect tray status. | Recording and paste behavior remain unchanged; any unverified paste remains explicitly unverified. |
| Motion and focus | Switch to Reduced Motion, hide and restore the pet, then return to VS Code. | No animation runs while hidden or reduced; focus remains on the editor. |
| Windowed browser video | Play and mute a local video in a normal browser window with no app rule. | Smart mode hides on sustained audible playback and restores after quiet. This detects audio, including music, not video content. A muted video stays visible. Use an app rule if you need a precise browser choice. |

Record the Windows build, FlowPilot executable hash, monitor arrangement, target applications, measured hide and restore times, focus result, and any false hide. Mark the feature complete only after those results are attached to the next release review. A passing `tests/run_all_tests.py --require-all` is a separate gate, not a substitute.
