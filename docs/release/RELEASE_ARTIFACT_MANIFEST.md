# Published Release Manifest

**Last reviewed:** 2026-10-18. This file records the published GitHub release; it does not certify the current `master` source or unpublished local pilot ZIPs.

| Field | Published v3.0.2 Windows release |
|---|---|
| Release | [`v3.0.2-release`](https://github.com/abishekvr0910/flowpilot/releases/tag/v3.0.2-release) |
| Source commit | `b9bd76396b2883fa2e87e8b131d231dc39c34515` |
| Download | [`FlowPilot-v3.0.2-win64.zip`](https://github.com/abishekvr0910/flowpilot/releases/download/v3.0.2-release/FlowPilot-v3.0.2-win64.zip) |
| Published asset size | 252,311,634 bytes |
| GitHub asset SHA-256 | `985e031c7af2617e4c03138d1a00472607ff9f9e1d2cff636827f26077f63f74` |

Verify your downloaded archive independently:

```powershell
Get-FileHash -Algorithm SHA256 .\FlowPilot-v3.0.2-win64.zip
```

The current `master` branch contains later pilot features and a separate test state. Check the [latest CI results](https://github.com/abishekvr0910/flowpilot/actions/workflows/ci.yml); do not use the v3.0.2 release report as proof of current `master` health. The [v3.0.2 evaluation](FLOWPILOT_V302_RELEASE_REPORT.md) is retained as a dated historical report. GitHub branch and tag protections are described separately in [governance status](../security/GITHUB_BRANCH_PROTECTION.md).
