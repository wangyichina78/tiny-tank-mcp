# CLAUDE.md

## QA/QC kit

The QA/QC kit lives in `docs/quality/`. When the owner says "update the QA/QC kit", or names a file such as "update QA-02", these are the files meant.

- **QA-00 is the single master test schedule.** Any other cadence, such as `docs/security_test_cadence.md`, maps its rows to QA-00 triggers. A new trigger goes into QA-00 first.
- **Keep the kit general.** Project-specific detail goes in the project's own docs, not in `docs/quality/`, except where a kit rule says to fill something in, such as the roles table.

## Standing instruction: quality-document updates

For changes to the QA/QC kit and the quality records (`docs/quality/`, `CHANGELOG.md`, `FINDINGS.md`, `docs/security_test_cadence.md`), the owner has said not to ask first:

1. Branch from the latest `main`, make the change, commit, open a PR and merge it to `main`.
2. Consolidate in the same PR:
   - add a `CHANGELOG.md` entry under `[Unreleased]` naming the PR;
   - log any defect, risk or process gap you notice in `FINDINGS.md`;
   - keep the `README.md` layout and the cross-references between documents accurate.
3. Each self-merge breaches QA-02 R2 (no independent review). Add the PR number to finding F10 in `FINDINGS.md`. Don't treat F10 as closed or as an accepted risk until a named security approver records it with an expiry date.
4. After merging, sync the working branch to `main` and push it.

**This does not cover code, CI or deployment config** (`src/`, `tests/`, `tools/`, `.github/`, `render.yaml`, `Dockerfile`, `security/`). For those, ask before merging. The one exception so far: the owner approved the F5 and F8 fixes (PR #5) on 2026-11-13.

## Records

- Versions use date plus commit, for example `2026-10-19_1ae0c97` (QA-01). Times are UTC-5.
- Never rewrite a past `CHANGELOG.md` entry or delete a finding. Add a correction or change the status (QA-01 R2, QA-04 R4).
- Evidence files follow the QA-03 naming rule and are stored outside the repository.
- No personal names, emails or secrets in these files. Refer to people by role (owner, reviewer, security approver).
