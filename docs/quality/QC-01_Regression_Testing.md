# QC-01 Regression Testing

**Question it answers:** did this change break anything that used to work?

Regression testing reruns the full set of automated tests on every change, so old behaviour is checked as carefully as new behaviour. It's the cheapest and most frequent QC check, and most of it runs without anyone pressing a button.

## 1. Test layers

Build the suite in layers, from fastest to slowest. Each layer catches what the one before it can't.

| Layer | What it tests | Speed | Runs |
|---|---|---|---|
| Unit | One function or rule in isolation, such as input validation or a calculation | Milliseconds | Every commit |
| Integration / protocol | Components working together through their real interfaces, such as the MCP SDK or a database client | Seconds | Every commit |
| Contract | The published interface hasn't changed unnoticed: schemas, tool definitions, API shapes | Seconds | Every commit |
| Smoke (live) | A running instance answers the key requests correctly | Seconds to a minute | Every deployment (QC-04) |

*Example (MCP package):* 13 unit tests on the business logic, 9 in-process protocol tests through the real SDK, a pinned hash of the published tool definitions as the contract test, and an 18-check live smoke test.

## 2. Writing a regression test, step by step

1. **Name what must stay true,** in one sentence: "An ID in the wrong format returns `INVALID_INPUT` and never echoes the input."
2. **Choose inputs that cover the boundaries:** a valid value, an invalid one, the edges (empty, too long, wrong type), and any input that broke things before.
3. **Write the expected result exactly.** Avoid "doesn't crash". Name the code, the value and the fields.
4. **Give the test a stable ID** (UT-07, IT-01) so findings, change log entries and reports can refer to it.
5. **Run it against the current code and watch it pass.** Then break the code deliberately, watch it fail, and restore the code (section 5).

## 3. Rules

**R1. Every fixed defect adds a test.** The test reproduces the defect, fails before the fix and passes after it. Record the test ID against the finding in QA-04.

**R2. The suite runs on the same versions as production.** If production runs Python 3.12, CI runs Python 3.12. When versions differ, run both. *Example:* a tool description came out differently on Python 3.12 and 3.13, which was caught only because CI ran both.

**R3. Green means all green.** A release needs 100% of the suite passing. There's no "known failures" list. A test that no longer applies is deleted through a reviewed change, with the reason recorded in QA-01.

**R4. No skipping, disabling or quarantining a test to get a release out.** If a test is wrong, fix the test in a reviewed change. If the code is wrong, fix the code.

**R5. Flaky tests are defects.** A test that passes and fails without a code change gets a findings entry (QA-04) and is fixed within one release cycle. One rerun is allowed, to confirm it's flaky. A second failure counts as real.

**R6. Contract changes need approval.** When a contract test fails because the interface changed on purpose, re-pin it only after review. The reviewer's name goes in the commit (QA-02).

## 4. Running the suite

Locally, before pushing:

```bash
python -m pytest -v
```

In CI, on every push and pull request, the pipeline:
1. installs pinned dependencies;
2. runs the full suite on every supported runtime version;
3. starts the service and runs the smoke test against it;
4. blocks the merge and the deployment if anything fails.

## 5. Prove the tests can fail

Once per significant change, and always for security-relevant tests, introduce a defect on purpose:

1. Make a copy of the file.
2. Introduce one specific defect (for example, echo the input back).
3. Run the suite. Record which tests failed and how many.
4. Restore the file and confirm the suite is green again.
5. Record the result in the test report (QA-03).

*Example:* switching the MCP server back to the plain SDK class made exactly the four tests written for that fix fail, and no others.

## 6. Report template

```
Regression report
Version:        <commit or tag>          Date/time: <YYYY-MM-DD HH:MM TZ>
Runtime(s):     <e.g. Python 3.12, 3.13>
Result:         <passed>/<total> passed   Duration: <s>
Failures:       <none | test IDs + one-line cause>
Deliberate-break check: <defect introduced> → <tests failed> → restored, green
Run by:         <name or CI run link>
```
