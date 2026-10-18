# FlowPilot Changelog

This page distinguishes published releases from work on `master`. Check [GitHub Releases](https://github.com/abishekvr0910/flowpilot/releases) for downloadable artifacts and [GitHub Actions](https://github.com/abishekvr0910/flowpilot/actions/workflows/ci.yml) for current verification status.

## Unreleased — current `master` source

- Added Companion Studio, additional pixel companions, meeting notes, productivity insights, selected-text transforms, and a dictation History Vault.
- The History Vault saves completed dictation text and WAV audio locally by default; see [PRIVACY.md](PRIVACY.md).
- Updated public documentation to separate current source from the published v3.0.2 artifact and to describe test limitations accurately.

These changes are **not** a published v3.1.0 release. Do not infer a passing regression gate from the v3.0.2 results; check live CI before packaging or promoting a new build.

## v3.0.2 — published October 15, 2026

- Windows portable release: [`FlowPilot-v3.0.2-win64.zip`](https://github.com/abishekvr0910/flowpilot/releases/tag/v3.0.2-release).
- The dated [release evaluation](docs/release/FLOWPILOT_V302_RELEASE_REPORT.md) records the hardware and corpus used for its measurements. Those results apply to that release, not automatically to later source.

Earlier engineering notes are retained as [historical snapshots](docs/archive/README.md); they are not a live feature list or current test report.
