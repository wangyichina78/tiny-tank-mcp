# Changelog

What changed in Tiny Tank MCP, newest first. Format and rules: [`docs/quality/QA-01_Change_Log.md`](docs/quality/QA-01_Change_Log.md).

Versions use date plus commit (QA-01 section 2), because this is a reference package. Times are UTC-5.

Entries before 2026-11-13 were **backfilled on 2026-11-13** from commit history, `docs/build_report.md` and `MCP_Publish.md`. No approver was recorded at the time, so those entries name none. Render deploys every push to `main` (finding F5), so each dated block below is what was live after that day.

## [Unreleased]

### Added
- QA/QC kit in `docs/quality/` (QA-00 to QA-04, QC-01 to QC-04). PR #1.
- `CHANGELOG.md` (this file) and `FINDINGS.md`, as the kit requires on day one. PR #3.

### Changed
- `docs/security_test_cadence.md` now maps each of its rows to the master cadence in QA-00 instead of keeping its own schedule. QA-00 and QC-02 gained two triggers: a published definition change, and a gateway or route change. PR #2.
- Re-pinning the tool-definition hash now needs the **security approver**, not any independent reviewer (QA-02). PR #2.
- The monthly black-box check now covers every live route, not only the direct endpoint. PR #2.
- The README layout lists the quality documents. PR #3.
- `CLAUDE.md` records how Claude Code sessions handle quality-document updates: merge without asking, consolidate the records, and log each self-merge in F10. PR #4.

### Fixed
- Render now deploys only after every CI check on the commit passes (`autoDeployTrigger: checksPass`), instead of deploying in parallel with CI (finding F5). PR #5.

### Security
- See Changed above: re-pin approval moved to the security approver.
- CI scans every tracked file for secrets with `detect-secrets` 1.5.0 on every push and pull request (finding F8, QC-02 R5). The deliberate SEC-05 fake is marked `pragma: allowlist secret`, and `.secrets.baseline` is empty. PR #5.
- `MCP_Publish.md` and `MCP_Security.md` now name the security approver for re-pins, matching QA-02. PR #5.

Approved by: none. PRs #1 to #5 were merged by their author without independent review, at the owner's direction (finding F10).

## [2026-10-23_09f33bf] — 2026-10-23

### Added
- `MCP_Guide.md`, `MCP_Publish.md` and `MCP_Security.md`.
- The reference package as a single zip in `dist/`, with the build date and time in the file name.

### Changed
- The MIT licence is replaced by a reference-only disclaimer (`DISCLAIMER.md`).

### Fixed
- Correction to `docs/build_report.md`: the smoke test runs 18 checks, not 17.

Verification: docs only, no code change since 2026-10-19_1ae0c97.

## [2026-10-19_1ae0c97] — 2026-10-19

### Added
- Three read-only tools: `list_tanks`, `get_inspection_history`, `get_tank_readings`.

### Changed
- The SEC-01 tool-definition pin now covers all four tools, sorted by name.

### Fixed
- Validation errors and unknown-tool errors no longer repeat the caller's input to the agent (finding F3, SEC-02 wrong-type and unknown-tool cases).

### Security
- F3 above was confirmed on the deployed Render server before the fix.

Verification: regression 79/79 on Python 3.12 and 3.13 · smoke 18/18 · security black-box 21/21 against a local live server (`docs/build_report.md`)

## [2026-10-17_3085a4e] — 2026-10-17

### Added
- Tiny Tank MCP: a read-only MCP server with one tool, `get_tank_status`, and the five security cases SEC-01 to SEC-05 with their cadence.
- Render deployment: the server honours `PORT`, and a `render.yaml` blueprint is added.

### Fixed
- Tool definitions no longer differ between Python 3.12 and 3.13, which had changed the SEC-01 hash (finding F4).
- The black-box security check counts a WAF refusal of an attack input as a pass, not an outage (finding F6).

Verification: tests 32/32 · smoke 9/9 · security black-box 21/21 against a local live server (`docs/build_report.md`). Container image build not verified locally (no Docker daemon); Render built it on deploy.
