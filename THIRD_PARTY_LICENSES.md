# Third-Party Components and License Review

FlowPilot application source is licensed under [MIT](LICENSE). The application also depends on third-party Python packages, native libraries, Qt components, and speech model assets. This page is an **inventory for review**, not a legal opinion or a claim that every notice has been audited in the packaged executable.

The direct runtime dependencies are listed in [pyproject.toml](pyproject.toml) and [requirements.txt](requirements.txt). Important packaged components include PySide6/Qt, faster-whisper, CTranslate2, ONNX Runtime, Silero VAD model assets, sounddevice/PortAudio, soundfile/libsndfile, NumPy, pywin32, pycaw, comtypes, pyperclip, and psutil. The final bundle may contain additional transitive dependencies.

## Graphical & Companion Assets Attribution

### SondeR-Cat (Optional Companion Sprites)
- **Component:** Pixel cat companion sprite definitions in [`ui/pet_sprites.py`](ui/pet_sprites.py).
- **Upstream Origin:** [Verisonder/SondeR-Cat](https://github.com/Verisonder/SondeR-Cat).
- **License:** [Apache License, Version 2.0](https://www.apache.org/licenses/LICENSE-2.0).
- **Attribution & Notice:** Based on SondeR cat by Verisonder. Copyright 2026 Verisonder. Licensed under Apache-2.0; FlowPilot adapts pixel matrix definitions for native PySide6/QPainter rendering. See the upstream [LICENSE](https://github.com/Verisonder/SondeR-Cat/blob/main/LICENSE) and [NOTICE](https://github.com/Verisonder/SondeR-Cat/blob/main/NOTICE). The upstream name identifies origin; it does not imply endorsement of FlowPilot.

Before distributing a new build:

1. Generate a dependency and model-asset inventory from the **actual packaged artifact**, including versions and sources.
2. Obtain each component's complete license and copyright notice from its installed distribution or upstream project. Do not rely on abbreviated excerpts or assumed license families.
3. Check Qt/PySide6 and other dynamically bundled native libraries against their applicable redistribution requirements with qualified counsel if distributing commercially.
4. Include all required notices with the release, then verify them in the extracted ZIP or installer.
5. Record the reviewed artifact hash and date so the notice set can be tied to one build.

The [published v3.0.2 asset](https://github.com/abishekvr0910/flowpilot/releases/tag/v3.0.2-release) predates this documentation cleanup. Its included notices should be inspected separately before making a compliance claim about that artifact.
