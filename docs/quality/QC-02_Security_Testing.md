# QC-02 Security Testing

**Question it answers:** can this be misused, and can we prove it can't?

Security testing starts from the threats, not from the code. Each test exists because a specific attack is possible, and each one has a pass condition that an independent person can check.

## 1. From threat to test, step by step

1. **List the assets:** what an attacker would want, such as data, the users' trust in the answers, or the systems behind the tool.
2. **List the entry points:** every place outside input arrives, such as API arguments, headers, files, other systems' outputs and the deployment pipeline.
3. **For each entry point, write the threats:** injection, data leakage, unauthorised actions, tampering, denial of service.
4. **For each threat, write a rule** (what the system must do) and **a test case** (how you'll prove it). Give each test case an ID: SEC-01, SEC-02 and so on.
5. **Record the threat → rule → test mapping in a table.** Every threat needs a test or a written reason why not.

*Example (MCP package):* five test cases covering tool poisoning (SEC-01), prompt injection through output (SEC-02), hidden side effects (SEC-03), transport attacks (SEC-04) and leakage through errors and logs (SEC-05).

## 2. Writing a security test case

Use this template for every case:

```
ID:          SEC-0X
Threat:      <what the attacker does, in one sentence>
Rule(s):     <the design rules this proves>
Inputs:      <attack inputs, listed: e.g. instruction override, SQL fragment, path traversal,
              non-ASCII look-alikes, invisible characters, oversized input, wrong data types>
Pass:        <exact, checkable conditions: codes, fields, "input appears nowhere in output">
Harnesses:   white-box (CI) | black-box (independent, against the deployed system)
Limits:      <what this test cannot prove>
```

Good attack inputs are specific and varied. A set of 8 to 12 per text input is typical. Include at least one that previously caused a defect.

## 3. Two harnesses, on purpose

| Harness | Who runs it | When | Proves |
|---|---|---|---|
| **White-box** | CI, with full access to the code | Every commit | The controls exist in the code |
| **Black-box** | An independent tester, with only the URL or the interface | Before each release, after each deployment, monthly while live | What an outsider actually experiences, through the real network path |

The black-box harness should need nothing but the address and a standard runtime, so someone outside the development team can run it from their own machine.

## 4. Rules

**R1. Independence.** The black-box run before release is done by someone who didn't write the change.

**R2. Prove the tests can fail.** For each test case, introduce the defect it targets at least once and confirm it fails (QC-01 section 5). *Example:* echoing input, poisoning a description, and adding a network call each made the right security tests fail.

**R3. Check the framework's defaults, not just your own code.** Libraries can have unsafe defaults. *Example:* the MCP SDK's validation error repeated the caller's input back to the AI. It was found only because a test sent a wrong-type argument.

**R4. A failed security test blocks release.** An exception can only be granted by the security approver, recorded as a findings entry with an expiry date (QA-04).

**R5. Scan for secrets on every commit,** with a scanner such as `detect-secrets` or GitHub's secret scanning. The only acceptable findings are deliberate fakes used in tests, and those must be recorded.

**R6. Record what the tests can't prove.** Every security report lists its limits. For example, an egress check that sees only Python-level calls.

## 5. When to run

| Trigger | Run |
|---|---|
| Every commit | White-box suite and secret scan |
| Before each release | Black-box check by an independent tester |
| After each deployment | Black-box check against the deployed address (part of QC-04) |
| Dependency, framework or platform upgrade | Both harnesses |
| Monthly while live | Black-box check |
| Interface or definition change | Both harnesses, plus re-approval of the contract pin (QA-02) |

## 6. Report template

```
Security test report
Version:      <commit/tag>         Target: <URL or environment>      Date/time: <YYYY-MM-DD HH:MM TZ>
Harness:      white-box | black-box        Run by: <name, role> (independent: yes/no)
Results:      SEC-01 <pass/fail> (<n>/<n> checks) ... SEC-0X ...
Refused upstream (WAF/gateway): <count and which inputs>
Failures:     <none | case, detail, findings ID>
Limits:       <what this run cannot prove>
Evidence:     <file name per QA-03>
```
