# QA-02 Change Control

**Question it answers:** who may change what, and what approval does each change need?

Change control makes sure every change to a live system is intended, reviewed, tested and approved in proportion to its risk, and that the trail survives for later. Most of it should be enforced by tools (branch protection, required checks, deployment gates) rather than by people remembering it.

## 1. Classify the change

| Class | Examples | Needs |
|---|---|---|
| **Standard** | Text fixes, documentation, internal refactoring with no behaviour change | Code review, green CI, change log entry |
| **Normal** | New features, changed behaviour, dependency upgrades | All of Standard, plus regression and security tests (QC-01, QC-02), UAT if behaviour changed (QC-03), and owner approval to release |
| **High-risk** | Interface or contract changes, security controls, authentication, data access, new external connections, any change to a published definition users or AIs read | All of Normal, plus security approver sign-off and an independent black-box test before release |
| **Emergency** | Fixing a live outage or an active security problem | Owner approval (can be verbal, recorded within 24 hours), the fastest safe test set, then full review and tests after the fact, within 2 working days |

When in doubt, use the higher class.

## 2. The change process, step by step

1. **Request:** an issue or ticket stating what, why, and the expected effect. Assign the class.
2. **Branch:** work on a branch, never directly on the main branch of a live system.
3. **Build with tests:** code, tests (every defect fix gets a regression test), and a change log entry under `[Unreleased]`.
4. **Pull request:** describe the change, link the request, list the tests run.
5. **Review:** by someone other than the author. The reviewer checks the code, the tests, and that the change log is accurate.
6. **Automated gates:** CI must be green. Branch protection blocks the merge otherwise.
7. **Merge.**
8. **Release approval:** for Normal and High-risk, the owner approves the release (and the security approver for High-risk), recording the version.
9. **Deploy:** only by the pipeline, only from green CI, with the artifact tagged by version.
10. **Verify:** release verification (QC-04). Roll back on failure.
11. **Close:** file the evidence (QA-03) and close the request.

## 3. Approvals that need a named person

Some decisions should never be automatic, because the approver is accepting responsibility for them:

| Decision | Approver | Recorded where |
|---|---|---|
| Release to production | Owner | Release record, change log "Approved by" |
| Re-pinning a contract or definition hash (the interface changed on purpose) | Security approver for anything users or AIs read; otherwise the reviewer | Commit message naming the approver |
| Accepting a security risk instead of fixing it | Security approver, with an expiry date | Findings register (QA-04) |
| Skipping a scheduled test or UAT | Owner | Change log entry, with the reason |
| Emergency change | Owner | Request, within 24 hours |

*Example:* in the MCP package, any change to a published tool definition failed the SEC-01 test until the new definition hash was reviewed and re-pinned. The person approving the new hash approves what every AI agent will read.

## 4. Enforce it with tools

| Control | How |
|---|---|
| No direct pushes to the main branch | Branch protection |
| Review required, author can't approve | Branch protection: one or more approvals, dismiss stale approvals on new commits |
| Tests must pass | Required status checks |
| Deploy only after CI | The deployment is a pipeline stage after the tests, not a separate trigger |
| Production needs approval | Pipeline environment protection with required reviewers |
| Versioned artifacts | Tag images and builds with the commit SHA. Never deploy `latest` |

## 5. Rules

**R1. No change reaches production outside this process.** That includes "small" configuration changes made in a platform dashboard. Record those as changes too.

**R2. Separation of duties:** the author can't be the only reviewer or the release approver for their own Normal or High-risk change.

**R3. Every approval is written** and traceable to a version.

**R4. Emergency changes are reviewed afterwards** without exception, and get a findings entry explaining the emergency.
