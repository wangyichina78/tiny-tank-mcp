# QA/QC Kit

A set of reusable quality documents for building, testing, changing and releasing software and digital tools, including AI tools. Each document stands on its own and includes fill-in templates.

## QA and QC: the difference

**Quality Control (QC)** checks the product. It finds defects in what was built, by testing it. Regression testing, security testing, user acceptance testing (UAT) and post-release checks are QC. QC answers: *does this thing work?*

**Quality Assurance (QA)** controls the process. It prevents defects, and it makes the work provable and repeatable: how changes are requested, approved, recorded and released. Change control, the change log, record keeping, the findings register and the test schedule are QA. QA answers: *can we prove we did it properly, and do it again?*

A team needs both. Passing every test doesn't help if nobody can show which version was tested or who approved it. Perfect paperwork doesn't help if the product was never properly tested.

## The documents

| File | Type | What it covers |
|---|---|---|
| `QA-00_Overview.md` | QA | The QA/QC split, how a change flows through the documents, roles, and **one master schedule for all testing**. Start here |
| `QC-01_Regression_Testing.md` | QC | Test layers, writing a regression test step by step, "every defect gets a test", no skipping tests, flaky tests, proving tests can fail, report template |
| `QC-02_Security_Testing.md` | QC | Turning threats into test cases, a security test case template, checks run in the pipeline vs by an independent tester, when to run, report template |
| `QC-03_User_Acceptance_Testing.md` | QC | When UAT is needed, preparing scenarios and acceptance criteria, testing AI systems with repeated runs scored as rates, sign-off form |
| `QC-04_Release_Verification.md` | QC | Checks before and after deploying, route comparison, the confirm-or-roll-back decision, rollback steps, report template |
| `QA-01_Change_Log.md` | QA | `CHANGELOG.md` format, versioning, entry template, rules (never rewrite history; rollbacks get entries) |
| `QA-02_Change_Control.md` | QA | Change classes (standard, normal, high-risk, emergency), an 11-step change process, approvals that need a named person, enforcing it with tools |
| `QA-03_Evidence_and_Record_Keeping.md` | QA | Which records to keep and for how long, a file-naming rule with timestamps, where to store them, logging rules, what must never be recorded |
| `QA-04_Findings_Register.md` | QA | Finding entry template, severity levels, lifecycle, risk acceptances that expire, and a worked example register |

## How to use it

1. Copy the files into a project's `docs/quality/` folder.
2. Read `QA-00_Overview.md` first, and fill in the roles table with names.
3. Create `CHANGELOG.md` (from QA-01) and `FINDINGS.md` (from QA-04) in the project root on day one, even if they start empty.
4. Remove anything that doesn't apply, and record the reason in the change log.

## Before you rely on it

- **The retention periods** in QA-03 (for example "life of the product + 1 year") are suggested starting points. Your company's records policy takes priority where it differs.
- **The severity targets** in QA-04 and **the emergency-change timings** in QA-02 (24 hours, 2 working days) are suggestions too. Adjust them to how your teams work.
- **The examples** come from an MCP server reference project and are labelled as such. The rules themselves are general.
