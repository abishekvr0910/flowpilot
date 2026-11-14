# GitHub branch protection: observed state and proposed policy

Checked 2026-11-14 for [abishekvr0910/flowpilot](https://github.com/abishekvr0910/flowpilot).

The [master branch endpoint](https://api.github.com/repos/abishekvr0910/flowpilot/branches/master)
reported `protected: true`, with the required-status-check summary showing
`enforcement_level: off` and no check contexts. The [rulesets endpoint](https://api.github.com/repos/abishekvr0910/flowpilot/rulesets?includes_parents=true)
returned an empty list. The detailed branch-protection endpoint returned HTTP 403
(`Resource not accessible by integration`), so this review cannot verify review,
administrator-bypass, force-push, or deletion settings.

This supersedes the October 18 observation that master had no protection.
Protected-branch metadata alone does not establish that every policy below is enabled.
This cleanup does not change repository protection settings.

## Proposed policy to verify in repository settings

1. Require pull requests and successful `ci.yml` checks before merge.
2. Require a qualified review when another maintainer is available; do not claim
   independent review for a single-maintainer project.
3. Prevent force pushes and branch deletion.
4. Add CODEOWNERS only for real reviewers.
5. Protect release tags where supported.

[Live CI](https://github.com/abishekvr0910/flowpilot/actions/workflows/ci.yml)
establishes the recorded run outcome, not tag immutability or policy enforcement.
