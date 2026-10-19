# FlowPilot security policy

**Scope:** current source, reviewed October 18, 2026. See [TRUST.md](TRUST.md) for evidence and release boundaries.

## Reporting a vulnerability

Do not publish vulnerability details in an ordinary issue. Use [GitHub private vulnerability reporting](https://github.com/abishekvr0910/flowpilot/security/advisories/new) if enabled. If that route is unavailable, use a previously verified private maintainer channel; do not assume an unlisted email address is monitored.

Include the source commit or release, Windows version, reproduction steps using synthetic data, impact, and relevant sanitized evidence. Maintainers triage reports as capacity permits. There is no contractual response-time guarantee.

## Version scope

Current development is identified in [pyproject.toml](pyproject.toml). The recorded published Windows artifact is [v3.0.2](docs/release/RELEASE_ARTIFACT_MANIFEST.md), which differs from current source. A fix in the working tree does not fix an older download. Security fixes need release notes and a new verified artifact before users can rely on them.

No multi-version security maintenance schedule is promised here. Check release notes for the status of a particular issue and build.

## Implemented boundaries and limits

| Area | Current design | Limit |
| --- | --- | --- |
| Speech recognition | CPU inference; model loader requests local files only; cloud STT is disabled. | Setup can download dependencies/models. Separately configured services and destination apps need separate review. |
| Dictation persistence | New profiles default to history off. Completed dictation persistence is gated by that setting. | Existing settings and records remain. Meetings, scratchpad, configuration, diagnostic output, and Windows facilities are separate. |
| Keyboard input | Windows shortcuts use Win32 registration; paste uses clipboard/keyboard paths with focus checks and recovery outcomes. | Focus can change; editor behavior and integrity levels vary. Cross-platform adapters use different input mechanisms. |
| Clipboard | Text backup and delayed restoration use content and sequence checks to avoid overwriting a newer copy. | Restoration is not immediate or dependent on successful verification, and it does not preserve all rich/image formats. The clipboard can be observed by other software. |
| Single instance | A named mutex coordinates desktop instances. | A mutex is coordination, not authentication or a defense against a malicious process running as the user. |
| Local integrations | The optional API requires a random 32+ character `FLOWPILOT_API_TOKEN` for REST and WebSocket routes, checks browser Origin, and is launched on loopback. Local LLM requests are restricted to loopback endpoints. | Do not share the token or bind/forward the server to other hosts. Token access does not isolate a malicious process running as the same user; request limits remain future work. |
| Saved files | Settings and optional records are local files. | FlowPilot does not provide its own encryption at rest. Windows account permissions and disk protection apply. |

The [network regression](tests/test_network_egress.py) intercepts selected socket operations in tested execution paths. It is not a runtime firewall, a full dependency audit, or independent certification.

## Operating guidance

Run normal dictation as a standard Windows user. If an elevated target refuses insertion, use Copy Last Dictation and manual paste. Do not make administrator execution the default troubleshooting step.

Keep the optional API on loopback; do not expose it through port forwarding, LAN binding, or public tunnels. Set a random `FLOWPILOT_API_TOKEN` of at least 32 characters before starting it, rotate the token if disclosed, and test each integration's Bearer-key support. Browser-origin and token checks are implemented; request-size/rate limits still need work. Other local software must not be assumed trustworthy merely because it connects from the same machine.

Review diagnostic output before sharing it: the current code can print foreground window titles, process names, filesystem paths, and exception details. Never send private recordings or your whole profile directory in a public report.

Download from the repository's release page and verify the matching artifact hash and executable signature. Hash matching does not establish publisher identity or safety. See the [release verification guide](docs/release/flowpilot_build_and_release.md). Do not disable Windows security features to make an unfamiliar build run.

## Assurance work still required

Release signing, exact-artifact dependency/license inventories, real interactive-desktop insertion measurements, and tighter API/diagnostic controls belong to the [release acceptance process](docs/release/flowpilot_build_and_release.md). No audit or compliance certification is asserted by this policy.
