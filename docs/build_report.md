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
| 2 | Done for the dry run: hosted on Render, smoke test and security check pass against it. Repeat with an independent tester on the company host | Developer, then an independent tester |
| 3 | Before connecting any organization's agent: get approval from that organization's security reviewer for calling a no-auth external endpoint | Whoever connects that agent |
| 4 | If routed through an MCP gateway: log its request-ID header next to `call_id` | Gateway owner |

## 4. Addendum: four tools (2026-10-19)

- **Tool set:** `list_tanks`, `get_inspection_history` and `get_tank_readings` added next to `get_tank_status`, over an 8-tank synthetic snapshot (`as_of` 2026-10-16). The tools return facts only; `get_tank_status` is unchanged.
- **Planted inconsistencies** for agents to find: TK-105 is in service with an overdue inspection and its level is above the high alarm; TK-107 is out of service but its level is rising.
- **Security finding, fixed:** the SDK's argument-validation error repeats the rejected value (`input_value=...`), and an unknown tool name is echoed back. Either one puts caller text in front of the agent. This affected the original `get_tank_status` too: it was confirmed on the deployed Render server before the fix. `TinyTankServer.call_tool` now rewrites both, naming only the field and what it expected. The SDK's own server log already records field names only.
- **SEC-01 pin:** now covers all four definitions, sorted by name. The hash is identical on Python 3.12 and 3.13.
- **Results:** 79/79 tests pass on Python 3.12 and 3.13. The smoke test passes 18/18 and the black-box security check passes 21/21 against a live local server. Switching back to the plain SDK class makes exactly the four new reflection tests fail.
