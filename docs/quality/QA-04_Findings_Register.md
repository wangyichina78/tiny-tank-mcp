# QA-04 Findings Register

**Question it answers:** what defects and risks have been found, who owns each one, and how was it closed?

The findings register is one list of everything found by any QC activity, by review, in production, or by a user. It is the memory of the project. Its value comes from three habits: every finding goes in, every finding has an owner, and nothing is closed without evidence.

## 1. Where it lives

One file, `FINDINGS.md`, in the project root. Or, for larger teams, the issue tracker with a "finding" label, linked from `FINDINGS.md`. Either way, one list.

## 2. What gets logged

Log it if any of these is true:

- a test failed for a reason other than a deliberate break (QC-01 section 5);
- a security test found a weakness, or the framework has an unsafe default;
- UAT found behaviour users didn't accept, including AI scenarios that pass only sometimes;
- release verification failed, or a release was rolled back;
- a test is flaky;
- a risk was accepted instead of fixed;
- a process failed: a check skipped, an approval missing, content published before review.

If it surprised anyone, log it. A finding closed as "not a problem" still teaches the next person something.

## 3. The entry

```markdown
### F3 — SDK validation errors echo caller input to the agent
- **Found:** 2026-10-19 by QC-02 (wrong-type argument case) · **Version:** 1ae0c97
- **Severity:** Medium · **Type:** Security
- **Description:** When an argument has the wrong type, the SDK's error message repeats the
  rejected value to the AI client. Unknown tool names are echoed too. Confirmed on the live deployment.
- **Root cause:** Framework default. The server didn't override error formatting.
- **Owner:** <name> · **Due:** <date>
- **Fix:** Override `call_tool` so errors name only the field and what was expected.
- **Regression test added:** SEC-02 wrong-type cases (3), unknown-tool case (1)
- **Verified:** Deliberate break (back to plain SDK class) made exactly these 4 tests fail. Black-box 21/21 on the deployed version.
- **Status:** Closed 2026-10-19 · **Change log:** 1.3.0 / Fixed
```

## 4. Severity

| Severity | Meaning | Target |
|---|---|---|
| Critical | Exploitable now, or users get harmful or wrong results now | Fix or roll back immediately. Emergency change (QA-02) |
| High | Serious weakness or wrong behaviour, with no workaround | Fix before the next release |
| Medium | Real weakness or defect, but limited impact or a workaround exists | Fix within two releases |
| Low | Minor defect or hardening improvement | Fix when convenient. Review quarterly |
| Information | Not a defect, but something to know: an environment quirk, a process lesson | Record and share. Close when documented |

Severity reflects impact if the issue were exploited or hit, judged by the owner and the security approver together. The finder proposes a rating and the owner confirms it.

## 5. Lifecycle

```
Open → Assigned (owner, due date) → In progress → Fixed (test added) → Verified (evidence) → Closed
                                   ↘ Accepted risk (security approver, expiry date) → reviewed at expiry
```

## 6. Rules

**R1. No finding is closed without evidence:** the regression test ID, and a test or verification report showing it passes.

**R2. Every fixed defect has a regression test** (QC-01 R1). The only exception is "Information" findings.

**R3. Accepted risks expire.** Each one has a named approver and an expiry date, and it reopens automatically at that date for a fresh decision.

**R4. Never delete a finding.** Mark it Closed, Duplicate (with a link), or Not a defect (with the reason).

**R5. Review open findings quarterly** with the owner and the security approver (QA-00 cadence). Anything past its due date needs a new date and a reason.

**R6. Link both ways:** the finding names its tests and its change log version, and the change log names the finding.

## 7. Example register (MCP reference package)

| ID | Finding | Severity | Status | Test |
|---|---|---|---|---|
| F1 | Rejected input reflected in a result field | Medium | Closed | SEC-02 (48 cases) |
| F2 | ID validation accepted non-ASCII digits | Low | Closed | SEC-02 (Arabic-Indic digits input) |
| F3 | SDK validation errors echo caller input | Medium | Closed | SEC-02 wrong-type and unknown-tool |
| F4 | Tool descriptions differed between Python 3.12 and 3.13 | Low | Closed | SEC-01, CI on both versions |
| F5 | Host deployed in parallel with CI | Medium | Open (enterprise pipeline) | Pipeline configuration |
| F6 | Edge firewall blocks attack strings on one route only | Information | Closed (parity exception agreed) | Route parity check |
| F7 | Browser-based clients rejected until their origin is allowlisted | Information | Closed (configuration step documented) | Release verification |
