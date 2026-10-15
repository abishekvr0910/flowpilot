# FlowPilot GitHub Branch Protection & Release Governance Specification

This document defines the formal branch protection rules and release tagging policies for the canonical FlowPilot repository (`https://github.com/abishekvr0910/flowpilot`).

---

## 1. Protected Branch: `master`

The `master` branch represents verified, reproducible, deployable releases. Direct pushes to `master` are strictly disallowed.

### Branch Protection Rules Settings

| Setting | Policy | Rationale |
| :--- | :--- | :--- |
| **Require a pull request before merging** | **Enabled** (minimum 1 approval) | Prevents untested or unreviewed code from entering production baseline. |
| **Dismiss stale pull request approvals when new commits are pushed** | **Enabled** | Ensures new commits receive explicit review. |
| **Require review from Code Owners** | **Enabled** (`CODEOWNERS`) | Core engine, security, and native Win32 changes require domain lead sign-off. |
| **Require status checks to pass before merging** | **Enabled** (Strict mode) | Branch must be up to date with `master` before merge. |
| **Required Status Checks** | `verify / Full-Stack Regression & Integration Suite` | Runs automated Python regressions (24 modules) and Node.js client test. |
| **Require conversation resolution before merging** | **Enabled** | All review comments must be addressed or resolved. |
| **Require signed commits** | **Enabled (Recommended)** | Cryptographically verifies committer identity. |
| **Require linear history** | **Enabled** (Squash or Rebase only) | Maintains clean git bisect capability and audit trails without messy merge bubbles. |
| **Do not allow bypassing the above settings** | **Enabled** (Enforce for Admins) | Guarantees release discipline even for repository administrators. |
| **Allow force pushes** | **Disabled** (Strictly blocked) | Prevents history rewrite or baseline destruction. |
| **Allow deletions** | **Disabled** (Strictly blocked) | Prevents accidental deletion of primary branch. |

---

## 2. Release Tag Protection Rules

Release tags mark immutable public artifacts and rollback baselines.

### Tag Protection Pattern: `v*` (e.g., `v3.0.2-release`, `v3.1.0-pilot`)

1. **Tag Immutability:** Never overwrite, retarget, or force-push an existing release tag.
2. **Authorized Tag Creation:** Only repository maintainers can create release tags.
3. **Artifact Consistency:** Every release tag must correspond to a verified commit whose tree matches the audited release manifest.
4. **Rollback Baselines:** All past release tags (specifically `v3.0.1-release` at `5fd8e2f` and `v3.0.2-release` at `b9bd763`) must remain permanently intact and accessible.

---

## 3. GitHub Actions Environment Secrets & Security

- **Zero Cloud Leakage in CI:** GitHub Actions workflows must not require or log cloud API keys (`GROQ_API_KEY`, `OPENAI_API_KEY`).
- **Offline Integrity:** Automated regression tests run with `engine_mode: "local"` and verify zero external network egress.
- **Dependency Pinning:** Python dependencies in `requirements.txt` and Node dependencies in `package.json` are pinned to prevent supply chain tampering.
