# Security Test Cadence: Can This Tool Harm the Agent That Calls It?

## Basis

No single Anthropic protocol certifies an MCP server as safe for the agent that calls it. These five cases are built from three sources:

- **MCP specification** (current revision 2026-07-28; security principles carried over from the 2025-06-18 and 2025-11-25 revisions). Tools are arbitrary code and must be treated with caution. Tool annotations are untrusted hints. Servers must validate Origin to prevent DNS rebinding.
- **OWASP MCP Top 10**, which is still in beta. The cases here cover tool poisoning (MCP03) and intent-flow subversion through prompt injection (MCP06).
- **OWASP Top 10 for Agentic Applications 2026**, specifically ASI02 (tool misuse).

The calling agent is Copilot Studio, not Claude. Guidance specific to Claude clients does not apply directly. The controls below are client-agnostic.

## Threat model for this tool

The attacker controls one of three things:

- the server or its deployment pipeline (rug pull, poisoned definition)
- the `tank_id` text (prompt injection reflected through the tool into the agent)
- the network path (DNS rebinding, cross-origin calls)

The asset is the calling agent's context and its other tools. One poisoned result could steer it to misuse them.

## The five cases

| ID | Threat | What is checked | Pass condition |
|---|---|---|---|
| **SEC-01** | Tool poisoning, rug pull | `tools/list` returns exactly one tool. Name, description, schemas, annotations and server instructions contain no injection markers (override phrases, `<IMPORTANT>` tags, URLs, shell verbs, credential words) and no hidden or non-ASCII characters. The SHA-256 of the definition as sent matches the pinned hash | All clean, hash equals `security/tool_manifest.sha256` |
| **SEC-02** | Indirect prompt injection through output | Adversarial inputs, 12 white-box and 8 black-box (instruction override, newline role switch, SQL, script tag, template, path traversal, Unicode digits, RTL override, zero-width space, URL exfil, NUL byte, 100 KB string) | `INVALID_INPUT`, `tank_id: null`, fixed message, no input text reflected, printable ASCII only, text content equal to structured content |
| **SEC-03** | Excessive agency, hidden side effects | Annotations are read-only, non-destructive, idempotent, closed-world. The declaration is identical at discovery and on every call. Repeat calls are identical. A Python audit hook during calls sees no `open`, `socket.*`, `subprocess.*`, `os.*` writes or `urllib.*`. The data is unchanged | Zero forbidden audit events, data unchanged |
| **SEC-04** | DNS rebinding, cross-origin calls, resource abuse | Foreign Host header, foreign Origin, 5 MB body. Hosted URL is HTTPS | Refused (421, 403, 413 or reset with the server still healthy). HTTPS when not on loopback |
| **SEC-05** | Information leakage, credential handling | A forced internal exception carries a fake secret and path. Malformed JSON-RPC. Wrong argument type. A credential canary is sent in `Authorization` and `X-Api-Key` | No secret, path, traceback or exception type reaches the agent. A wrong-type argument is refused, not run. The canary never appears in any log |

## Two harnesses, on purpose

| Harness | Who runs it | Covers | Why |
|---|---|---|---|
| `tests/test_security.py` (white-box, 17 tests) | Developer and CI, on every change | SEC-01..05 in full, including the audit hook and forced exception | Proves the controls are in the code |
| `python -m tools.security_check --url <deployed>/mcp` (black-box, 21 checks) | **Independent tester**: someone who did not write the code | SEC-01..05 over the network against the real deployment. The SEC-03 egress check is limited to declarations, so egress must also be shown by the container network policy | Proves what the agent actually sees, through the real ingress and gateway |

Independence matters here. A developer running their own checks on their own laptop proves less than a second person running the black-box script against the URL the agent uses.

**The tests themselves were checked.** Three deliberate breaks were introduced: echoing input back, a poisoned description, and network egress with open-world set. The suite caught all three (12, 1 and 6 failures), then passed again after the code was restored.

## Cadence

| Trigger | Harness | Owner | Evidence kept |
|---|---|---|---|
| Every commit or PR | White-box | Developer (CI) | CI log |
| Before each deployment | Black-box on the deployed URL, direct and gateway route | Independent tester (a security reviewer or a peer who did not write the code) | `evidence/security-<date>.json` |
| `mcp` SDK version bump or base-image change | Both | Developer, then independent tester | Both |
| Gateway route or policy change | Black-box on the gateway URL | Gateway owner and independent tester | Evidence file |
| Monthly while the direct endpoint is live | Black-box | Independent tester | Evidence file |
| Tool definition changed (SEC-01 hash fails) | Stop. Review the diff, re-pin with `--pin`, re-run both | Developer proposes, independent reviewer approves the pin | Pin commit with reviewer named |

The re-pin is the control point. Whoever approves a new hash approves what the agent will read.

## Known limits

- **Python-level egress test only.** The audit hook would not see native-code egress. The container egress-deny policy is the real control.
- **Pattern-based injection detection.** The marker list catches known patterns, not novel phrasing. It works because the output surface is tiny and fixed, not because pattern matching is complete.
- **No authentication.** No authentication is acceptable only for synthetic test data on an endpoint that is taken down when testing ends. Real data needs OAuth (MCP authorization spec) and a re-run of all five cases.
