# Security Declaration: Tiny Tank MCP

Declaration version 1.0. Applies to the tool definition pinned in `security/tool_manifest.sha256`.

## What the server declares

The server sends this declaration twice, both times in machine-readable form:

- **At discovery:** in the tool definition, before any call (`tools/list` → `tools[0]._meta["tinytank/security-declaration"]`).
- **On every call:** in the result (`tools/call` → `result._meta["tinytank/security-declaration"]`).

The declaration sits in `_meta`, not in the text the model reads. That way it cannot become a channel for instructions.

| Property | Declared | Enforced by | Verified by |
|---|---|---|---|
| `read_only` | true | No write path exists in code | SEC-03 (data unchanged after calls) |
| `side_effects` | none | Pure in-memory dictionary lookup | SEC-03 (audit hook: no files, sockets, processes) |
| `network_egress` | false | No network code; container egress policy | SEC-03 (no `socket.*`/`urllib.*` audit events) |
| `filesystem_access` | false | No file I/O in the tool path | SEC-03 (no `open` audit events) |
| `code_execution` | false | No eval, exec or subprocess | SEC-03 |
| `data_classification` | synthetic-test-data | Three hard-coded made-up records | Code review |
| `reflects_caller_input` | false | Rejected input is never echoed; only validated `TK-###` IDs return | SEC-02 |
| `instructions_in_output` | false | Output text is server-authored and fixed | SEC-02 |
| `authentication` | none (public test endpoint, synthetic data only) | Synthetic data only, read-only tool; host rate limiting | SEC-04 (HTTPS on hosted URL) |

The server also sets the standard MCP tool annotations: `readOnlyHint: true`, `destructiveHint: false`, `idempotentHint: true`, `openWorldHint: false`.

## How a calling agent should treat this

The MCP specification says tool annotations are **untrusted hints** unless they come from a trusted server. A malicious server could send the same declaration. The declaration has value only together with three things:

1. **Pinned manifest.** The live tool definition hash matches `security/tool_manifest.sha256` (SEC-01). If it doesn't match, the definition changed after review. Do not connect.
2. **Current evidence.** An independent SEC-01..05 run on the deployed URL is no older than the cadence in `docs/security_test_cadence.md` allows.
3. **Platform controls.** The hosting platform keeps the network controls in place: ingress allowlist, egress deny, TLS.

## Reporting

Report suspected vulnerabilities privately through GitHub's private vulnerability reporting (the repository's **Security** tab, then **Report a vulnerability**). Do not open a public issue.
