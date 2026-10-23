# Companion visibility interactive gate

The new companion visibility code is a development build after RC2. Do not call it released until these checks have been performed on an interactive Windows desktop. Automated policy tests are necessary but cannot prove that Chrome, PowerPoint, VS Code, and the tray behave together on a real display.

Use a fresh test profile and a distinct single instance mutex when launching the development executable from `scratch/companion-visibility-build-20261022/dist/FlowPilot/FlowPilot.exe`. Keep the RC2 archive unchanged. If another FlowPilot instance already owns the hotkey, close it normally before checking F9. Do not terminate processes by generic name.

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
| Windowed browser video | Play video in a normal Chrome window with no app rule. | This version does not automatically identify it. Use a manual `chrome.exe` app rule if preferred; that rule affects the whole browser, including nonvideo work. |

Record the Windows build, FlowPilot executable hash, monitor arrangement, target applications, measured hide and restore times, focus result, and any false hide. Mark the feature complete only after those results are attached to the next release review. A passing `tests/run_all_tests.py --require-all` is a separate gate, not a substitute.
