# FlowPilot release reassessment — 2026-10-22

This is a measured review of the local working tree, not a declaration of a finished or published product. It supersedes the release-status claims in older handoff notes and the earlier review's 51-suite baseline. No files were committed or pushed during this reassessment.

## What was actually changed

- Restored live Windows target-process and self-window detection by importing `os` and `psutil` in `engine/text_injector.py`. Previously broad exception handling silently swallowed `NameError` in both paths.
- Made `engine/config.py::save_config` write to a flushed temporary file and atomically replace the config under a process-local lock. An interrupted serialization now leaves the previous JSON intact.
- Restricted spoken tab insertion to explicit commands (`press tab`, `tab key`, `insert tab`); ordinary prose such as “The browser tab crashed” is no longer corrupted.
- Corrected all three meeting-report decision extraction sites to remove the complete Markdown prefix.
- Removed a misleading UIA test that preloaded the target text before simulated paste and could therefore claim confirmed insertion without proving delivery. Confirmation now requires the expected text count to increase over a pre-dispatch document snapshot. Unreadable targets remain `SENT_UNVERIFIED`.
- Isolated every suite's config profile, bounded each child suite to 240 seconds, and added `--require-all` so a release gate fails on skips. The first strict run exposed a false skip label caused by the new regression test printing a synthetic `[SKIP]` marker; that marker is now captured inside the test.

Focused regression tests cover each change. A direct Notepad run physically found the inserted text and preserved the prior clipboard, although the injector itself conservatively returned `SENT_UNVERIFIED` when read-back did not prove the change within its window. That distinction is intentionally preserved.

## Evidence obtained

| Check | Result and boundary |
|---|---|
| Strict source gate | `python -X utf8 tests/run_all_tests.py --require-all`: **53 passed, 0 skipped, 0 failed**, 162.12 seconds on the available interactive desktop. The four physical desktop suites executed rather than skipping. |
| Focused tests | `pytest -q tests/test_release_integrity_fixes.py tests/test_target_verification_modern_apps.py`: 8 passed. Direct `test_text_injector.py` passed with physical Notepad buffer and clipboard checks. |
| UI rendering | `scripts/preview_workspace.py` rendered Home, Studio, Settings, Scratchpad and Meetings at 1160×820 and 880×580 in Sand and Obsidian themes (20 images). Home, compact Home, Meetings and compact Obsidian Settings were visually inspected. This is not a full interactive usability test. |
| Fresh build | PyInstaller 6.22.3 built a new isolated Windows directory from the current source. `dist/FlowPilot/` now contains that build; the former unpacked build was moved recoverably to `scratch/archive-pre-RC2-FlowPilot-20261022-01/`. |
| Binary smoke | Final `dist/FlowPilot/FlowPilot.exe` passed bundled-asset checks, isolated named-mutex ownership, duplicate-instance exit and clean termination. |
| Offline self-test | The staged build loaded bundled Faster-Whisper base weights and transcribed the SAPI fixture with offline flags and an isolated empty HF cache: exit code 0, 1.57-second transcription, zero cache files. This is not a whole-system packet capture or general latency benchmark. |
| RC2 archive | `dist/FlowPilot-v3.1.0-RC2-win64.zip`: 772,927,221 bytes, SHA-256 `682A7FFC39516FA1C2733D4275E8383D1B5603E46DBA859FC85F7DBAB1B0C51E`. ZIP CRC passed; embedded EXE matches unpacked EXE SHA-256 `FD3E2D7825E6AEDBC745215FF8E64EBD8F561F4E00B01B5FB408AE597304CAC0`. |
| Archive hygiene | 1,232 ZIP members; filename scan found no copied competitor renderer, credential bridge, `flow.sqlite`, or `__pycache__` paths. This does not establish a full software-bill-of-materials or rights audit. |

## Release decision: candidate only

RC2 is suitable for further local pilot testing, **not** a general release sign-off. Local `master` was 26 commits ahead of `origin/master` when checked, and the local `v3.1.0-release` tag was absent remotely. The new fixes are uncommitted, so the ZIP is not reproducible from a single published commit. The executable is `NotSigned`. No CI run on this exact source revision, broad customer-machine test, thousand-trial paste reliability study, or real-human multilingual accuracy study was completed in this pass. “Zero bugs,” “100% focus reliability,” regulatory compliance and Wispr Flow superiority would therefore be unsupported claims.

The package is about 1.11 GB unpacked. The bundled `small` model is 461.1 MiB and `base` is 138.5 MiB. Removing `small` would shrink the install materially but would change offline multilingual capability; that is a product decision, not a safe cleanup operation.

## Remaining technical and product work, ordered

1. **Release provenance:** review and commit the source delta, run remote CI on that exact commit, rebuild/re-hash from it, then decide whether to publish/sign. Do not reuse this ZIP hash after rebuilding.
2. **Insertion evidence:** run repeated first-pass/recovery trials in Notepad, VS Code, browser editors and Terminal with the user desktop active. Keep `SENT_UNVERIFIED` for opaque or unchanged buffers. UIA read-back was directly exercised on a Qt editor only; cross-app coverage and its cross-thread COM behavior are not established by the current test.
3. **Loopback API hardening:** `engine/server.py` still creates an orchestrator at import; the audio upload reads the whole file without a size cap; non-ASCII bearer values may turn `compare_digest` into a 500. These were confirmed by source inspection but not changed after the package build.
4. **Human-language quality:** measure English/Hindi/Tamil/Malayalam on consented real voices, including code-switching and identifier/factual error rates, before advertising language parity. Synthetic SAPI results are not a real-speaker benchmark.
5. **UX quality:** preview screenshots show a stable native layout in both themes, but some Meetings control glyphs rendered as fallback squares in the offscreen preview and compact navigation requires scrolling. Test the actual installed UI with keyboard, screen reader and high-DPI settings before calling it polished.
6. **Workspace cleanup:** keep `dist/FlowPilot/` and RC2 ZIP as the current local candidate. Historical `dist/FlowPilot_backup_*` directories and older ZIPs remain in place because `tests/test_silero_vad_resolution.py` and historical release documents reference them. Decouple tests from those backup paths and fix references before archiving them. The old current build was moved, not deleted. `scratch/` also contains older generated build/preview/profile directories; no broad recursive deletion was performed. Avoid inspecting or moving the ignored `.flowpilot-endpoint-test-18936.json` until its ownership and sensitivity are established.

Current engineering instructions and the release manifest were updated to state the 53-suite gate and local-candidate status. Archive documents and existing untracked `AGENTS.md`/`CLAUDE.md` context files still contain older counts; they should be reviewed separately rather than silently overwritten.
