# Verification Report

Date: 2026-10-17
Environment: Linux, Python 3.13, `mcp` 2.3.0 from PyPI.
Endpoint: `/mcp` (Streamable HTTP, stateless, JSON responses). Local: `http://127.0.0.1:8000/mcp`.

## 1. What was verified

| Check | Result |
|---|---|
| SDK interface: `mcp.server.mcpserver.MCPServer`, `run(transport="streamable-http", host, port, streamable_http_path, stateless_http, json_response, transport_security)` | Confirmed against the installed 2.3.0 source |
| `pytest`: 15 functional tests (UT-01..07, discovery, in-process tool calls, log line) and 17 security tests (SEC-01..05) | 32/32 pass |
| `tools/smoke_test.py` on a live server, 2025-06-18 `initialize` handshake | 9/9 checks pass (initialize, tools/list, 7 calls) |
| `tools/security_check.py` (black-box) on a live server | 21/21 checks pass |
| Wrong path `/wrong` | Exit 2, HTTP 404 |
| `MCP_HOST=0.0.0.0` with `MCP_ALLOWED_HOSTS=127.0.0.1:*` | Smoke test passes. `Host: evil.example.com` gets HTTP 421 |
| SDK `Client` in `auto` mode over HTTP (2026-07-28 revision path) | TK-102 returns OK, Inspection Due |
| Server log | Exactly one JSON line per call, no credentials |
| Security tests catch real defects | Three deliberate breaks (echoing input, a poisoned description, network egress) were each caught |
| Container image build | **Not verified**. No Docker daemon in the build environment |

## 2. Design decisions

- **Business logic is separate from the MCP wrapper.** `business_logic.py` has no SDK import, so it can be unit tested on its own.
- **Bad input returns a result, not a tool error.** `INVALID_INPUT` and `NOT_FOUND` come back as normal results with a fixed `message`, so the agent can respond ("ask again" or "not found"). Only unexpected exceptions become MCP tool errors, and their details stay in the server log.
- **Rejected input is never echoed.** For `INVALID_INPUT`, `tank_id` is `null`. Caller text, possibly a prompt-injection attempt, never comes back into the agent's context.
- **Strict validation.** The ID must be a full match of ASCII `TK-[0-9]{3}` after trimming and upper-casing. Python's `\d` would also accept non-ASCII digits.
- **One fixed output shape.** All six fields are always present. Agents map fields more reliably when the shape never changes.
- **`source` field.** It lets the agent say where the answer came from.

## 3. Open items

| # | Item | Owner |
|---|---|---|
| 1 | Build and run the Docker image on a host with a daemon | Developer |
| 2 | Host on a public HTTPS endpoint and run `tools/security_check.py` against it | Developer, then an independent tester |
| 3 | Before connecting any organization's agent: get approval from that organization's security reviewer for calling a no-auth external endpoint | Whoever connects that agent |
| 4 | If routed through an MCP gateway: log its request-ID header next to `call_id` | Gateway owner |
