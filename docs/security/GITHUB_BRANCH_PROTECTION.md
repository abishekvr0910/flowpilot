# GitHub Branch Protection: Current State and Target Policy

**Checked:** 2026-10-18. **Repository:** [`abishekvr0910/flowpilot`](https://github.com/abishekvr0910/flowpilot).

At review time, GitHub's branch-protection endpoint returned no protection for `master`, the repository rulesets API returned an empty list, and no `CODEOWNERS` file was tracked. Therefore the following items are **proposed controls, not enabled protections**. Check [branch rules](https://api.github.com/repos/abishekvr0910/flowpilot/rulesets?includes_parents=true) and the repository settings again before asserting any control is active.

## Proposed `master` rules

1. Require pull requests and passing `ci.yml` checks before merge.
2. Require at least one review when another qualified maintainer is available; do not claim independent approval if the project is single-maintainer.
3. Prevent force pushes and branch deletion.
4. Add a `CODEOWNERS` file only when real owners can review the listed paths.
5. Protect release tags if the GitHub plan and repository settings support the intended enforcement.

The v3.0.2 release tag is a published artifact, but publication does not prove tag immutability or branch protection. The [live CI workflow](https://github.com/abishekvr0910/flowpilot/actions/workflows/ci.yml) is the current source of test status.
