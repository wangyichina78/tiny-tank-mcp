# Findings Register

Every defect, risk and process gap found in Tiny Tank MCP. Format, severity and rules: [`docs/quality/QA-04_Findings_Register.md`](docs/quality/QA-04_Findings_Register.md).

**Created 2026-11-13.** F1 to F7 are backfilled. F3 to F7 come from `docs/build_report.md`, `MCP_Publish.md` and commit history. F1 and F2 appear only in the QA/QC kit's example register, and the repo describes them as design choices, not as defects found. Each entry gives its source.

**No owners are assigned yet**, because the roles table in QA-00 is blank (F9). Severities are as proposed by the finder, and the owner confirms them (QA-04 section 4). Due dates will be set once an owner is named.

## Summary

| ID | Finding | Severity | Status | Test |
|---|---|---|---|---|
| F1 | Rejected input reflected in a result field | Medium | Closed | SEC-02 |
| F2 | ID validation accepted non-ASCII digits | Low | Closed | SEC-02 (non-ASCII digit input) |
| F3 | SDK validation errors echo caller input | Medium | Closed | SEC-02 wrong-type and unknown-tool |
| F4 | Tool descriptions differed between Python 3.12 and 3.13 | Low | Closed | SEC-01, CI on both versions |
| F5 | Render deploys in parallel with CI | Medium | **Open** | None yet |
| F6 | WAF blocks attack strings on one route only | Information | Open: parity exception not yet agreed | Route parity check |
| F7 | Browser-based clients rejected until their origin is allowlisted | Information | Closed | Release verification |
| F8 | No secret scan in CI | Medium | **Open** | None yet |
| F9 | No named owner, reviewer or security approver | Medium | **Open** | None (process) |
| F10 | PR #1 and PR #2 merged without independent review | Low | **Open** | None (process) |

## Entries

### F1 — Rejected input reflected in a result field
- **Found:** before 2026-10-17 · **Version:** before 9ed41b3
- **Severity:** Medium · **Type:** Security
- **Source:** QA/QC kit example register only. The repo records the rule ("rejected input is never echoed", `docs/build_report.md`) but not the defect itself.
- **Description:** Text rejected by validation was returned in a result field, putting caller text into the agent's context.
- **Regression test added:** SEC-02 (`tank_id: null` on `INVALID_INPUT`, no input text reflected)
- **Verified:** SEC-02 passes, 79/79 on 2026-10-19_1ae0c97
- **Status:** Closed (backfilled; original closure date not recorded)

### F2 — ID validation accepted non-ASCII digits
- **Found:** before 2026-10-17 · **Version:** before 9ed41b3
- **Severity:** Low · **Type:** Security
- **Source:** QA/QC kit example register. `docs/build_report.md` records the rule: Python's `\d` also matches non-ASCII digits, so IDs must fully match ASCII `TK-[0-9]{3}`.
- **Regression test added:** SEC-02 non-ASCII digit input
- **Verified:** SEC-02 passes, 79/79 on 2026-10-19_1ae0c97
- **Status:** Closed (backfilled; original closure date not recorded)

### F3 — SDK validation errors echo caller input to the agent
- **Found:** 2026-10-19 by QC-02 (wrong-type argument case) · **Version:** before 1ae0c97
- **Severity:** Medium · **Type:** Security
- **Description:** When an argument has the wrong type, the SDK's error message repeats the rejected value (`input_value=...`) to the agent. Unknown tool names are echoed too. Confirmed on the deployed Render server.
- **Root cause:** Framework default. The server didn't override error formatting (QC-02 R3).
- **Fix:** `TinyTankServer.call_tool` rewrites both errors, naming only the field and what was expected.
- **Regression test added:** SEC-02 wrong-type cases (3), unknown-tool case (1)
- **Verified:** Switching back to the plain SDK class made exactly these 4 tests fail. 79/79 and black-box 21/21 after the fix (`docs/build_report.md`).
- **Status:** Closed 2026-10-19 · **Change log:** 2026-10-19_1ae0c97 / Fixed

### F4 — Tool descriptions differed between Python 3.12 and 3.13
- **Found:** 2026-10-17 by CI (failed on Python 3.12 only) · **Version:** 9ed41b3
- **Severity:** Low · **Type:** Defect
- **Description:** Descriptions taken from docstrings came out differently on 3.12 and 3.13. That changed what agents see, and the SEC-01 hash.
- **Fix:** explicit description strings (commit 3084b4d). CI runs both versions.
- **Regression test added:** SEC-01 hash check, run in CI on 3.12 and 3.13
- **Verified:** The hash is identical on both versions (`docs/build_report.md`)
- **Status:** Closed 2026-10-17 · **Change log:** 2026-10-17_3085a4e / Fixed

### F5 — Render deploys in parallel with CI
- **Found:** 2026-10-17 during the Render dry run · **Version:** 724c18b onward
- **Severity:** Medium · **Type:** Process
- **Source:** `MCP_Publish.md` sections 7 and 12
- **Description:** Render's auto-deploy and CI both start on the same push and run independently, so a commit that fails CI is deployed anyway. It caused no harm in the dry run. `render.yaml` still has `autoDeploy: true` as of 2026-11-13.
- **Fix:** make deploy a pipeline stage after CI passes, or turn off `autoDeploy` and deploy by hook from CI.
- **Owner:** unassigned · **Due:** set when an owner is named
- **Status:** Open

### F6 — WAF blocks attack strings on one route only
- **Found:** 2026-10-17 on Render (Cloudflare) · **Version:** 724c18b
- **Severity:** Information · **Type:** Environment
- **Description:** Cloudflare returned HTTP 403 for inputs such as `TK-102; DROP TABLE tanks` and `../../etc/passwd`. The direct route and the gateway route therefore give different answers for attack inputs. The security check first mistook this for an outage.
- **Fix:** the security check counts a 4xx on an attack input as refused upstream (commit 3085a4e).
- **Open item:** `MCP_Publish.md` says to agree "blocked at the edge" with security as an accepted parity difference. No record of that agreement exists. Close this finding once the security approver (F9) records it.
- **Status:** Open (check fixed; parity exception not yet agreed)

### F7 — Browser-based clients rejected until their origin is allowlisted
- **Found:** in the parallel agent-eval session, adding the server as a claude.ai connector · **Version:** not recorded
- **Severity:** Information · **Type:** Configuration
- **Description:** The connection failed with only a generic error until `https://claude.ai` was added to `MCP_ALLOWED_ORIGINS`. Copilot Studio may send its own origin.
- **Fix:** documented as a configuration step in `MCP_Publish.md` section 4. Never set `*`.
- **Status:** Closed (configuration step documented)

### F8 — No secret scan in CI
- **Found:** 2026-11-13 while reconciling the security cadence with QA-00 · **Version:** 3a0b554
- **Severity:** Medium · **Type:** Security / process
- **Description:** QC-02 R5 requires a secret scan on every commit. `.github/workflows/ci.yml` has none. The deliberate fake secrets used by SEC-05 will need to be recorded as accepted findings once a scanner runs.
- **Fix:** add a scanner (for example `detect-secrets`, or GitHub secret scanning) to CI.
- **Owner:** unassigned · **Due:** set when an owner is named
- **Status:** Open

### F9 — No named owner, reviewer or security approver
- **Found:** 2026-11-13 while adopting the QA/QC kit · **Version:** 3a0b554
- **Severity:** Medium · **Type:** Process
- **Description:** The roles table in QA-00 is blank. Several controls depend on a named person: re-pin approval (QA-02), risk acceptance (QA-04 R3), the parity exception (F6), and closing findings.
- **Fix:** fill in the QA-00 roles table.
- **Owner:** unassigned · **Due:** set when an owner is named
- **Status:** Open

### F10 — PR #1 and PR #2 merged without independent review
- **Found:** 2026-11-13 · **Version:** d2b7a94, 3a0b554
- **Severity:** Low · **Type:** Process
- **Description:** Both PRs were merged by their author without a reviewer. This breaches QA-02 R2. Both are docs only. PR #2 changed who approves a security re-pin, so it changed a process control.
- **Fix:** the security approver reviews PR #2 after the fact and records the outcome here.
- **Owner:** unassigned · **Due:** set when an owner is named
- **Status:** Open
