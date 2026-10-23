# Tiny Tank MCP

A small, read-only MCP server for testing how an agent (Claude, Copilot Studio, or any MCP client) combines tools. It serves four tools over Streamable HTTP at `/mcp` (stateless, JSON responses) on a synthetic dataset of 8 tanks at two sites.

There are no write operations, no connections to any other system, no auth, and no secrets.

## Tools

| Tool | Input | Returns |
|---|---|---|
| `list_tanks` | `site` (optional: `Site A` or `Site B`) | Tank ID, site, product, capacity |
| `get_tank_status` | `tank_id` (`TK-###`) | Status and site |
| `get_inspection_history` | `tank_id` | Inspections (date, type, result, notes), `next_due` |
| `get_tank_readings` | `tank_id`, `days` (1-7, default 7) | Daily level % and temperature, high and low alarm limits |

Every result carries `result_code` (`OK`, `NOT_FOUND`, `INVALID_INPUT`), a fixed `message` and `source`. The newer tools also return `as_of`, the date of the data snapshot (2026-10-16). Rejected input is never echoed back.

The tools return facts only. They never say "overdue" or "alarm". Working that out is the agent's job.

## Try it with an agent

Two tanks are deliberately inconsistent, and no single tool shows the problem:

- **TK-105** is "In Service", but its inspection was due 2026-09-30 and its level has been above the 90% high alarm for 5 days.
- **TK-107** is "Out of Service", but its level rose from 0.5% to 37.6% in a week.

Ask questions like these and watch which tools the agent calls:

- "Which tanks at Site B need attention, and why?"
- "Are any tanks overdue for inspection?"
- "Is anything happening in a tank that's out of service?"
- "Compare Site A and Site B."

## Layout

```
MCP_Guide.md              how MCP works and how to build a server, step by step
MCP_Publish.md            how to host it: container, config, TLS, pipeline, gateway, agents
MCP_Security.md           security rules, the SEC-01..05 tests, evidence and limits
src/tank_data.py          the synthetic snapshot (8 tanks, inspections, 7 days of readings)
src/business_logic.py     validation and lookups (no MCP dependency)
src/server.py             MCP wrapper, run options, one JSON log line per call
tests/                    unit, in-process MCP protocol, and security (SEC-01..05) tests
tools/smoke_test.py       stdlib client for a live endpoint; writes JSON evidence
tools/compare_routes.py   direct vs gateway evidence parity check (GT-05)
tools/security_check.py   black-box SEC-01..05 against a live endpoint
security/tool_manifest.sha256  pinned hash of the tool definitions (SEC-01)
SECURITY.md               security declaration
docs/security_test_cadence.md  the five security cases and when to run them
docs/deployment.md        hosting and connecting an agent
docs/build_report.md      verification results
.github/workflows/ci.yml  tests + live black-box security check on every push
```

## Run locally

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python -m pytest -v                 # 79 tests (22 functional + 57 security)
python -m src.server                # http://127.0.0.1:8000/mcp
python tools/smoke_test.py --out evidence/direct.json
```

## Runtime variables

| Variable | Default | Purpose |
|---|---|---|
| `MCP_HOST` | `127.0.0.1` | Bind interface (`0.0.0.0` in the container) |
| `MCP_PORT` | `$PORT`, else `8000` | Listen port. Hosting platforms that set `PORT` work unchanged |
| `MCP_ALLOWED_HOSTS` | empty | Comma-separated Host header allowlist |
| `MCP_ALLOWED_ORIGINS` | empty | Comma-separated Origin allowlist |

When `MCP_HOST` is a loopback address, the SDK applies a localhost-only Host/Origin check on its own. On any other bind, set `MCP_ALLOWED_HOSTS`. Otherwise no Host header check runs.

## Logging

Each tool call writes one JSON line to stderr with these fields: `ts`, `event`, `tool`, `call_id`, `tank_id` (or `site` for `list_tanks`; normalized, max 32 characters), `result_code`, `duration_ms`. Headers, tokens and other arguments are never logged.

## Security

Every tool declares itself read-only, non-destructive, idempotent and closed-world. It does this through standard MCP annotations and a `tinytank/security-declaration` block in `_meta`, sent both at discovery and on every call. See `SECURITY.md`.

The five security cases (SEC-01..05) and when they run are in `docs/security_test_cadence.md`. Run the independent black-box check with:

```bash
python -m tools.security_check --url http://127.0.0.1:8000/mcp --log-file server.log
```

## Connect an agent

Once hosted at `https://<host>/mcp` (see `docs/deployment.md`):

```bash
claude mcp add --transport http tiny-tank https://<host>/mcp
```

For Copilot Studio, add an MCP tool with the Streamable HTTP transport and no authentication. If the agent belongs to an organization, get that organization's approval before connecting it to an external endpoint.

## License

MIT
