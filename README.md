# Tiny Tank MCP

A minimal, read-only MCP server for testing agent-to-tool integration. An agent (Claude, Copilot Studio, or any MCP client) looks up a tank's status from a defined source instead of making the answer up. It runs one read-only MCP tool, `get_tank_status`, over Streamable HTTP at `/mcp`. The endpoint is stateless and sends JSON responses.

The data is three synthetic tanks. There are no write operations, no connections to any other system, no auth, and no secrets.

| Input | `result_code` | `status` | `site` |
|---|---|---|---|
| `TK-101` | `OK` | In Service | Site A |
| `TK-102` | `OK` | Inspection Due | Site A |
| `TK-103` | `OK` | Out of Service | Site A |
| any other `TK-###` | `NOT_FOUND` | null | null |
| wrong format (`TANK-102`, empty) | `INVALID_INPUT` | null | null (`tank_id` also null: rejected input is never echoed) |

Input is trimmed and upper-cased before validation, so `tk-102` resolves to `TK-102`. Every result has the same six fields: `tank_id`, `status`, `site`, `result_code`, `message`, `source`.

## Layout

```
src/business_logic.py     synthetic records, validation, lookup (no MCP dependency)
src/server.py             MCP wrapper, run options, one JSON log line per call
tests/                    unit, in-process MCP protocol, and security (SEC-01..05) tests
tools/smoke_test.py       stdlib client for a live endpoint; writes JSON evidence
tools/compare_routes.py   direct vs gateway evidence parity check (GT-05)
tools/security_check.py   black-box SEC-01..05 against a live endpoint
security/tool_manifest.sha256  pinned hash of the tool definition (SEC-01)
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
python -m pytest -v                 # 32 tests (15 functional + 17 security)
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

Each tool call writes one JSON line to stderr with these fields: `ts`, `event`, `tool`, `call_id`, `tank_id` (normalized, max 32 characters), `result_code`, `duration_ms`. Headers, tokens and other arguments are never logged.

## Security

The tool declares itself read-only, non-destructive, idempotent and closed-world. It does this through standard MCP annotations and a `tinytank/security-declaration` block in `_meta`, sent both at discovery and on every call. See `SECURITY.md`.

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
