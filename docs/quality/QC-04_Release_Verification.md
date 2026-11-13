# QC-04 Release Verification

**Question it answers:** is the version we just deployed actually working, in the real environment?

Tests in CI prove the code works on a build server. Release verification proves the deployed system works where users reach it: through the real network, TLS, gateway, firewall and configuration. Many failures exist only there. *Examples:* a corporate proxy blocking the host, a firewall blocking certain inputs, a client rejected because its origin wasn't on an allowlist.

## 1. Before deploying

1. **Confirm CI is green on the exact commit being deployed.** Not on a nearby one.
2. **Confirm the release is approved** under change control (QA-02).
3. **Confirm the change log entry exists** for this version (QA-01).
4. **Note the version currently live and its image or artifact ID.** That's the rollback target.

## 2. After deploying, step by step

Run these from outside the platform, against the real address.

1. **Version check:** confirm the deployed version matches the one that was approved. Check the commit, tag or image ID in the platform. A deployment that silently served the old version passes every functional check.
2. **Smoke test:** a fixed set of requests with known answers.
   ```bash
   python tools/smoke_test.py --url https://<host>/<path> --timeout 90 --out evidence/<file per QA-03>
   ```
3. **Security check (black-box):** run QC-02's black-box harness against the deployed address.
4. **Route parity (if there's a gateway or proxy):** run the smoke test through each route and compare the results field by field. Agree in advance which differences are acceptable. *Example:* a web firewall blocking attack strings on one route only.
5. **Configuration check:** allowlists, environment variables and feature flags have their intended values. Never record secret values. Record only that they're set.
6. **Real client check:** connect at least one real client, such as the agent platform users will use, and run one UAT scenario.
7. **Logs:** confirm the deployed instance writes its logs to the expected place, in the expected format, with no secrets in them.

## 3. Decide

| Result | Action |
|---|---|
| All checks pass | Release confirmed. File the evidence (QA-03) and close the change |
| A check fails, cause clear and fix small | Roll back first, then fix through a normal change. Don't fix forward on a live system without the owner's approval |
| A check fails, cause unclear | Roll back. Log a finding (QA-04). Investigate on the test environment |
| Couldn't run a check (network, access) | Not verified. The release stays unconfirmed until the check runs. Record the blocker |

**Rollback, step by step:**
1. Redeploy the previous approved version by its exact artifact ID.
2. Rerun steps 1 and 2 above against it.
3. Record the rollback in the change log (QA-01) and the cause in the findings register (QA-04).

## 4. Rules

**R1. Deploy only from green CI.** The pipeline enforces it. *Example:* a hosting platform that auto-deployed in parallel with CI would have shipped a failing commit, so deployment was made a stage after CI.

**R2. Artifacts are named by version,** never `latest`, so evidence and rollback point to exactly one build.

**R3. Someone other than the author runs the verification** for production releases.

**R4. Free or sleeping test hosts aren't production.** Cold starts and shutdowns make results unreliable. Always-on instances are required for real use.

## 5. Report template

```
Release verification
Version deployed: <commit/tag/image ID>    Previous version: <ID>     Environment: <name>
Date/time:        <YYYY-MM-DD HH:MM TZ>     Verified by: <name>
Version check:    match / mismatch
Smoke:            <passed>/<total>
Security (black-box): <passed>/<total>, refused upstream: <n>
Route parity:     PASS / FAIL (<accepted differences>)
Config check:     OK / <issues>
Real client:      <client>, scenario <UAT-ID>: pass/fail
Decision:         Confirmed | Rolled back to <ID> | Unverified: <blocker>
Evidence:         <file names per QA-03>
```
