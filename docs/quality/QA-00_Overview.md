# QA-00 Overview: How the QA and QC Documents Fit Together

This kit is a set of reusable rules and templates for building, testing, changing and releasing software or digital tools, including AI tools such as MCP servers. Each document stands on its own. This overview explains the split, the order of work, who does what, and the master test cadence.

## QA and QC

The two terms are often used interchangeably, but they mean different things.

**Quality Control (QC)** checks the product. It finds defects in what was built, by testing it. A failed QC check means "this version is not good enough to release."

**Quality Assurance (QA)** controls the process. It prevents defects and makes the work provable: how changes are requested, reviewed, approved, recorded and released. A QA gap means "even if this version is fine, we couldn't prove it, or repeat it."

A team can pass every test and still fail QA, because nobody can show which version was tested, who approved it, or why a change was made. The opposite also happens: perfect paperwork around a product nobody tested properly. Both halves are needed.

## The documents

| Document | Type | Answers |
|---|---|---|
| QA-00 Overview (this file) | QA | How it all fits, who does what, when tests run |
| QC-01 Regression Testing | QC | Did this change break anything that used to work? |
| QC-02 Security Testing | QC | Can it be misused, and can we prove it can't? |
| QC-03 User Acceptance Testing (UAT) | QC | Does it do what the business user actually needs? |
| QC-04 Release Verification | QC | Is the deployed version working, in the real environment? |
| QA-01 Change Log | QA | What changed, when, why, and in which version? |
| QA-02 Change Control | QA | Who may change what, and what approval is needed? |
| QA-03 Evidence and Record Keeping | QA | What records we keep, where, how named, and for how long |
| QA-04 Findings Register | QA | Every defect and risk found, its owner, and how it was closed |

## The flow of one change

```
Request → QA-02 classify and approve → build → QC-01 regression → QC-02 security
       → QA-01 change log entry → QC-03 UAT (when behaviour changes) → QA-02 release approval
       → deploy → QC-04 release verification → QA-03 file the evidence
       Any defect found anywhere → QA-04 findings register
```

## Roles

Assign the roles before work starts. One person can hold more than one, with one exception: **the person who wrote a change can't be its only reviewer or its independent tester.**

| Role | Responsibility |
|---|---|
| Owner | Accountable for the product. Approves releases and accepts residual risk |
| Developer | Builds the change, writes and runs automated tests, updates the change log |
| Reviewer | Reviews the change before it merges. Must not be the author |
| Independent tester | Runs security and release checks against the deployed version. Must not be the author |
| Business user (UAT) | Runs acceptance scenarios and signs off on behaviour |
| Security approver | Approves the security design, high-risk changes and any accepted security risk |

## Master test cadence

This is the single schedule. The other documents give the detail for each row.

| Trigger | What runs | Who | Evidence kept (QA-03) |
|---|---|---|---|
| Every commit or pull request | QC-01 regression suite, and the automated part of QC-02 | CI (automated) | CI run log |
| Before merging | Code review | Reviewer | Review approval in the pull request |
| Before every release | Full QC-01 and QC-02. QC-03 if behaviour changed | Developer, independent tester, business user | Test reports, UAT sign-off |
| After every deployment | QC-04 release verification, including the QC-02 black-box check against the deployed address | Independent tester | Verification report, security report |
| Dependency or platform upgrade | QC-01 and QC-02 in full | Developer, then independent tester | Test reports |
| Published interface or definition change (for example, a pinned contract hash no longer matches) | Stop the release. Review the change, re-approve the pin (QA-02), then QC-01 and QC-02 in full | Developer proposes, security approver approves the pin, independent tester re-runs | Pin commit naming the approver, test reports |
| Gateway, proxy or network route change | QC-02 black-box check and QC-04 route parity on the changed route | Route owner, independent tester | Security report, verification report |
| Monthly, while live | QC-02 independent black-box check on every live route | Independent tester | Security report |
| Quarterly | Review open findings (QA-04) and this cadence | Owner and security approver | Review minutes |
| Any incident | Root cause, a new regression test, a findings entry | Developer and owner | Findings entry, test added |

A project may keep a more detailed cadence for one area, such as which harness runs against which URL. Each of its rows must map to a row here. A new trigger is added here first, then to the detailed cadence, so the two can't drift apart.

## Principles behind every document

1. **No release without green checks.** The pipeline enforces it, rather than people remembering to.
2. **Every defect gets a test.** A bug that is fixed without a test that would have caught it will come back.
3. **Prove the tests work.** Break the code on purpose once, and confirm the tests fail. A test that has never failed proves little.
4. **Independence.** Whoever built it doesn't sign it off alone.
5. **Evidence over statements.** "Tested" means a stored report with a version, a date and a result.
6. **Honest limits.** Write down what the tests can't prove.

## Adopting the kit

1. Copy the files into the project's `docs/quality/` folder.
2. Fill in the roles table with names.
3. Delete any rows that don't apply. Never delete a row silently: record why in QA-01.
4. Create `CHANGELOG.md` (QA-01) and `FINDINGS.md` (QA-04) in the project root on day one, even if they start empty.
