# QA-03 Evidence and Record Keeping

**Question it answers:** what records do we keep, where, how are they named, and for how long?

"Tested" means nothing without a record: which version, what ran, when, who ran it, and what the result was. This document defines which records to keep, a naming rule that makes them findable, and what must never appear in them.

## 1. What to keep

| Record | Produced by | Contains | Keep at least |
|---|---|---|---|
| CI run logs | The pipeline, on every commit | Test results per runtime, commit ID | 90 days (the platform default is often shorter; export the release runs) |
| Regression reports | QC-01, per release | Report template from QC-01 | Life of the product + 1 year |
| Security reports, white-box and black-box | QC-02 | Report template, plus the JSON evidence file | Life of the product + 1 year |
| UAT scenarios, results and sign-off | QC-03 | Scenarios, actual answers, rates, signed decision | Life of the product + 1 year |
| Release verification reports | QC-04 | Report template, plus evidence files | Life of the product + 1 year |
| Change log | QA-01 | Version history | Permanent (lives in the repo) |
| Approvals | QA-02 | Who approved what version, when | Life of the product + 1 year |
| Findings register | QA-04 | All findings and their lifecycle | Permanent (lives in the repo) |
| Runtime logs | The running system | One structured line per request (section 4) | Per company logging policy, typically 30 to 90 days |

The retention periods are a starting point. Check them against your company's records policy, which wins where it's longer.

## 2. Naming rule

Every evidence file name answers four questions: what, which system, which version, and when.

```
<type>_<system>_<version>_<YYYY-MM-DD>_<HHMM>[_<environment>].<ext>
```

Examples:
```
security-blackbox_tiny-tank-mcp_9af84d6_2026-10-19_1430_render.json
smoke_tiny-tank-mcp_9af84d6_2026-10-19_1431_render.json
uat-signoff_tiny-tank-mcp_1.3.0_2026-10-21_0900.pdf
regression_tiny-tank-mcp_9af84d6_2026-10-19_1402.txt
```

- **Dates use ISO format** (`YYYY-MM-DD`), so files sort in time order.
- **Time is 24-hour,** in one time zone stated in the project README. Packages handed to others carry the timestamp in the file name too.
- **The version is the exact commit, tag or artifact ID,** never "latest" or "final".

## 3. Where to store it

- **In the repository:** the change log, the findings register, test code, and the pinned contract hashes.
- **In an evidence store** (a controlled SharePoint library, a document management system, or an artifacts store): the reports and evidence files, in one folder per system and version: `evidence/<system>/<version>/`.
- **Not in personal drives or email threads.** Evidence someone else can't find doesn't exist.
- **Generated evidence stays out of the code repository** unless it's small and final. Large or frequent output goes to the evidence store.

## 4. Runtime logging rules

Applications should write one structured line per request:

```json
{"ts": "2026-10-19T14:31:02.118+00:00", "event": "tool_call", "tool": "get_tank_status",
 "call_id": "5a77b13d...", "tank_id": "TK-102", "result_code": "OK", "duration_ms": 0.016}
```

- **Always include:** timestamp (UTC), event, operation, a unique call ID, the validated subject (truncated), the result code, and the duration.
- **Never log:** passwords, tokens, API keys, authentication headers, full raw input, or personal data beyond what's necessary.
- **Encode as JSON,** so a newline inside input can't fake a log line.
- **Prove it:** a test sends a fake credential (a "canary") and fails if it appears in any log. That's part of QC-02.
- **Correlate:** if a gateway adds a request ID, log it next to the call ID, so one request can be traced end to end.

## 5. What must never be in any record

- Secrets: passwords, tokens, keys, connection strings. Record that a secret is set, never its value.
- Personal data not needed for the record's purpose.
- Internal names, sites or systems in records that leave the organisation or go to a public repository. Review anything before publishing it.
- Links to private chat or AI session histories in records that will be shared outside the team.

## 6. Rules

**R1. Evidence is created by the tool, not typed by hand,** wherever possible. Scripts write JSON or text reports, and people sign off on them.

**R2. Records aren't edited after the fact.** Corrections are new records that reference the old one.

**R3. Every release has a complete evidence set** before it's confirmed: regression, security, UAT (if needed), release verification and approval.

**R4. Review the evidence store once a quarter** (QA-00 cadence). Check that the most recent release has a full set and that retention is being applied.
