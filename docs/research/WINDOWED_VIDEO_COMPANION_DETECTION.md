# Windowed video detection, October 2026

FlowPilot now has a conservative Smart companion mode for fullscreen windows and Windows presentation state. This note records why the same build does not claim to recognize every video playing inside an ordinary browser window.

Microsoft's Global System Media Transport Controls can report a media session's source app, playback status, and, when supplied, a playback type such as `Video` or `Music`. Those values do not identify the foreground browser tab or its visible rectangle. A browser can play a video in a background tab while the user types in another tab of the same process. Some players do not publish this metadata at all. Therefore an app level `Playing` or even `Video` signal cannot prove that a windowed video is visible beneath the companion. See [session identity](https://learn.microsoft.com/en-us/uwp/api/windows.media.control.globalsystemmediatransportcontrolssession), [playback info](https://learn.microsoft.com/en-us/uwp/api/windows.media.control.globalsystemmediatransportcontrolssessionplaybackinfo), and [media types](https://learn.microsoft.com/en-us/uwp/api/windows.media.mediaplaybacktype).

Current safe behavior:

1. Fullscreen video and Windows presentation states trigger Smart hiding.
2. A person can set an app rule to `Hidden`, `Edge`, or `Normal` in Companion Studio for any ordinary sized player or browser. This is an app rule, not video recognition.
3. `Always show` and `Show companion now` remain explicit overrides; F9 and tray feedback continue while hidden.

To ship automatic windowed recognition, first prove a local, opt in signal that ties active video playback to the exact foreground window or tab without collecting page text, titles, URLs, screen pixels, or audio. Test Chrome, Edge, Firefox, VLC, paused video, background music, background tabs, two monitors, and browser picture in picture. Record false hide and missed hide rates. If the signal cannot meet that bar, keep per app controls rather than silently hiding the pet for all browser audio.
