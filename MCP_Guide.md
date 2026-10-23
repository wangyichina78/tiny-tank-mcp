<!--
Brief (for the author, delete before circulating)
Reader: a Python developer in IT who has never built or used MCP.
Hard claim: an MCP server is an ordinary web service that publishes a menu of functions. The LLM sits in the client, and it can only call what the server's code defines.
Kept thin: protocol internals, resources, prompts, stdio transport.
Kept off the page: company names, real sites, the author's personal hosting account.
-->

# MCP Guide: How MCP Works and How to Build a Server

> **Reference material only.** This is not production software. Review and vet it fully before using any part of it, and don't adopt it into a work environment as it is. Whoever uses it takes full responsibility for that use. See [DISCLAIMER.md](DISCLAIMER.md).

This guide guides a Python developer to build a working, tested MCP server. Every command and every output shown here was run against the MCP Python SDK 2.3.0 on Python 3.12 and 3.13. The reference implementation is the Tiny Tank server in this package (`src/`). Publishing is covered in `MCP_Publish.md`, and the security rules in `MCP_Security.md`.

## 1. The mental model

The most common misunderstanding is that an MCP server is an AI. It isn't. **An MCP server contains no language model.** It is a small web service that tells an AI application, "here are the functions I offer, and here is what each one does." The AI application decides when to call them.

Three parties are involved:

```
 User: "What's the Brent price?"
        │
        ▼
 ┌──────────────────────────┐        MCP (JSON-RPC over HTTPS)        ┌─────────────────────────┐
 │ AI APPLICATION (client)  │ ── tools/list ────────────────────────► │ MCP SERVER (your code)  │
 │ Copilot Studio, Claude,  │ ◄─ menu: names, descriptions, schemas ─ │                         │
 │ ChatGPT, VS Code, ...    │                                          │  get_price(symbol)      │
 │                          │ ── tools/call get_price {"symbol":..} ► │  list_tanks(site)       │
 │  contains the LLM, which │ ◄─ result (JSON) ─────────────────────── │  ...                    │
 │  plans and writes the    │                                          │  calls your DB / API    │
 │  answer                  │                                          └─────────────────────────┘
 └──────────────────────────┘
```

A single question runs through five steps:

1. **Connect.** When the application connects to your server, it calls `tools/list`. Your server returns its menu: one entry per tool, each with a name, a description and a JSON Schema for the inputs.
2. **Show.** The application puts that menu in front of the LLM, next to the user's question.
3. **Choose.** The LLM reads the descriptions and decides whether a tool helps. If one does, it doesn't write prose. It outputs a structured request, `call get_price with {"symbol": "BRENT"}`.
4. **Execute.** The application sends `tools/call` to your server. Your Python function runs and returns JSON.
5. **Answer.** The application gives the result to the LLM. The LLM either writes the reply or decides to call another tool first.

Two consequences follow, and the rest of this guide is built on them.

**The LLM never runs your code and never touches your systems.** It can only ask the application to call a tool that your server lists, with arguments that your code then validates. If your server has no `update_*` tool, nothing the user types can cause an update. Read-only is a property of your code, not a promise from the model.

**The LLM picks tools purely from text.** It never sees your implementation. It sees the tool name, the description and the input schema, and nothing else. A vague description produces wrong tool choices. This is why tool design (section 7) is where most of the real engineering happens.

If an analogy helps: MCP is to an AI application what ODBC is to a reporting tool. It's a standard plug, so any compliant client can use any compliant server without custom integration code. MCP was created by Anthropic in 2024 and is now governed by the Agentic AI Foundation under the Linux Foundation. Copilot Studio, Claude, ChatGPT, Gemini, VS Code and Cursor all act as MCP clients.

## 2. What a server can offer

An MCP server can expose three kinds of things. Tools are the one that matters for most business use, and they are the only one this package uses.

| Kind | What it is | Who triggers it | Example |
|---|---|---|---|
| **Tools** | Functions with typed inputs and outputs | The LLM decides | `get_tank_status(tank_id)` |
| Resources | Read-only documents or data the client can load | The application or the user | A tank manual, a schema description |
| Prompts | Reusable task templates the user picks from a menu | The user | "Weekly tank health review for site ___" |

## 3. Transports: how the bytes travel

MCP messages are JSON-RPC 2.0. Two transports carry them:

- **stdio:** the client starts your server as a local subprocess and talks over stdin and stdout. It's common for desktop tools, and it isn't used here.
- **Streamable HTTP:** your server is a web service with one endpoint, conventionally `/mcp`. The client POSTs JSON-RPC messages to it. This is what a hosted, shared server uses, and what a gateway can sit in front of.

This package runs Streamable HTTP with two options that make it behave like a plain REST service:

- `stateless_http=True`: no session is kept between requests, so any replica can serve any request, and load balancers and gateways need no sticky sessions.
- `json_response=True`: replies are plain JSON rather than an event stream, which is easier to proxy, log and test with `curl`.

## 4. Setup

You need Python 3.12 or later.

```bash
python -m venv .venv
. .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install "mcp>=2.3,<3.0" pytest
```

**A warning about examples on the web.** Most MCP tutorials published before 2026 use SDK version 1, where the class was `FastMCP`, imported from `mcp.server.fastmcp`. In version 2 it is `MCPServer`, imported from `mcp.server.mcpserver`, and the HTTP options moved from the constructor to `run()`. If you copy an old example and get `ModuleNotFoundError: No module named 'mcp.server.fastmcp'`, that is the cause. Pin the major version (`<3.0`) so this doesn't happen to you again silently.

## 5. Build your first server, step by step

Create `hello_mcp/server.py` (with an empty `hello_mcp/__init__.py` next to it):

```python
from typing import TypedDict

from mcp.server.mcpserver import MCPServer
from mcp_types import ToolAnnotations

mcp = MCPServer(
    "hello-mcp",
    instructions="Tools for looking up product prices. Answer only from tool results.",
)

PRICES = {"WTI": 71.40, "BRENT": 75.10}


class PriceResult(TypedDict):
    symbol: str | None
    price_usd: float | None
    result_code: str
    message: str


@mcp.tool(
    description="Return the latest price in USD for a product symbol (WTI or BRENT).",
    annotations=ToolAnnotations(read_only_hint=True, destructive_hint=False,
                                idempotent_hint=True, open_world_hint=False),
)
def get_price(symbol: str) -> PriceResult:
    key = symbol.strip().upper()
    if key not in PRICES:
        return PriceResult(symbol=None, price_usd=None, result_code="NOT_FOUND",
                           message="Unknown symbol. Valid symbols: WTI, BRENT.")
    return PriceResult(symbol=key, price_usd=PRICES[key], result_code="OK",
                       message=f"{key} is {PRICES[key]} USD.")


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8765,
            streamable_http_path="/mcp", stateless_http=True, json_response=True)
```

What each part does:

**`MCPServer("hello-mcp", instructions=...)`** creates the server. The name identifies it to clients. `instructions` is a short paragraph the client may pass to its LLM as guidance for using your tools as a group. Clients differ in whether they pass it on, so never rely on it for anything that matters.

**`@mcp.tool(...)`** registers the function as a tool. The function name becomes the tool name unless you pass `name=`.

**`description=`** is the single most important line in the file, because it is what the LLM reads to decide whether to call this tool. Always pass it explicitly as a string. If you leave it out, the SDK uses the docstring. Python 3.13 strips docstring indentation and 3.12 does not, so the same code then publishes a different description depending on the runtime. We hit exactly this in testing.

**Type hints become the input schema.** `symbol: str` becomes `{"symbol": {"type": "string"}}`, and the parameter is required because it has no default. A parameter with a default (`days: int = 7`) becomes optional. The SDK validates incoming arguments against these types before your function runs.

**The return type becomes the output schema.** Returning a `TypedDict` (or a Pydantic model) makes the SDK publish an `outputSchema` and send the result as `structuredContent`, which clients can map field by field. It also sends a text copy for older clients.

**`annotations=`** are labels that describe the tool's behaviour: read-only, non-destructive, idempotent, and closed-world (it doesn't reach outside systems). Clients use them for display and confirmation prompts. **They enforce nothing.** A badly written tool labelled read-only can still write. Your code is the control.

**The function body is ordinary Python.** In a real server it calls your database or internal API. Return a result with a `result_code` for expected outcomes (not found, invalid input) rather than raising, so the LLM gets something it can explain to the user.

## 6. Test it before any AI is involved

### In-process, no network

The SDK includes a client that connects to a server object directly. This is the fastest test loop and belongs in `pytest`:

```python
import asyncio

from mcp import Client

from hello_mcp.server import mcp


async def main():
    async with Client(mcp) as client:
        tools = (await client.list_tools()).tools
        print("tools:", [t.name for t in tools])
        result = await client.call_tool("get_price", {"symbol": "wti"})
        print("result:", result.structured_content)


asyncio.run(main())
```

Output:

```
tools: ['get_price']
result: {'symbol': 'WTI', 'price_usd': 71.4, 'result_code': 'OK', 'message': 'WTI is 71.4 USD.'}
```

### Over HTTP, looking at the actual messages

Start the server with `python -m hello_mcp.server`. Then send the same three messages an AI client sends.

**1. Handshake.** The client says which protocol version it speaks, and the server replies with its capabilities and instructions:

```bash
curl -s http://127.0.0.1:8765/mcp \
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"curl","version":"1"}}}'
```

```json
{"jsonrpc": "2.0", "id": 1, "result": {
  "capabilities": {"prompts": {"listChanged": false}, "resources": {"listChanged": false, "subscribe": false}, "tools": {"listChanged": false}},
  "instructions": "Tools for looking up product prices. Answer only from tool results.",
  "protocolVersion": "2025-06-18",
  "serverInfo": {"name": "hello-mcp", "version": ""}}}
```

**2. Discovery.** This is the menu the LLM will read. Send the same headers plus `MCP-Protocol-Version: 2025-06-18`, with the body `{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}`. The reply, with the output schema shortened:

```json
{"tools": [{
  "name": "get_price",
  "description": "Return the latest price in USD for a product symbol (WTI or BRENT).",
  "inputSchema": {"type": "object", "properties": {"symbol": {"title": "Symbol", "type": "string"}}, "required": ["symbol"]},
  "annotations": {"readOnlyHint": true, "destructiveHint": false, "idempotentHint": true, "openWorldHint": false},
  "outputSchema": {"title": "PriceResult", "required": ["symbol", "price_usd", "result_code", "message"], "...": "..."}
}]}
```

**3. A call.** This is what the client sends when the LLM decides to use the tool. Body: `{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"get_price","arguments":{"symbol":"brent"}}}`. The reply:

```json
{"content": [{"type": "text", "text": "{\n  \"symbol\": \"BRENT\", ... }"}],
 "isError": false,
 "structuredContent": {"symbol": "BRENT", "price_usd": 75.1, "result_code": "OK", "message": "BRENT is 75.1 USD."}}
```

That is the whole protocol for a tool server: `initialize`, `tools/list`, `tools/call`. Everything else is detail.

### With a real agent

To see an LLM use your server, point an MCP client at it.

- **Claude Code:** `claude mcp add --transport http hello http://127.0.0.1:8765/mcp`, then ask "What's the Brent price?"
- **MCP Inspector:** a browser-based test client from the MCP project. Run it with `npx @modelcontextprotocol/inspector` and connect it to the URL. It's useful for checking schemas and calls by hand.
- **Copilot Studio** can't reach `127.0.0.1`. It needs a published HTTPS address, which is covered in `MCP_Publish.md`.

## 7. Designing tools: where the real work is

A working server is easy. A server that an LLM uses reliably and safely takes deliberate design. These rules come from building and testing Tiny Tank.

**Write descriptions for a reader who has nothing else.** State what the tool returns, the input format with an example (`format TK-###, for example TK-102`), the units, and anything easy to misread. `get_tank_readings` says levels are percent of capacity and temperatures are in °F, because an LLM will otherwise guess.

**Prefer several narrow tools to one clever one.** Tiny Tank has four: `list_tanks`, `get_tank_status`, `get_inspection_history` and `get_tank_readings`. None of them answers "which tanks need attention?" alone. Asked that question about Site B, an agent made 13 calls and combined the results. It found an in-service tank with an overdue inspection running above its high-level alarm, an out-of-service tank whose level was rising, and a third tank trending toward its low alarm that nobody had planted. The reasoning belongs in the agent. A tool that tried to answer the question itself would hide that reasoning and would be much harder to test.

**Return facts and leave judgement to the agent.** The tools return `next_due` and `as_of`, and never "overdue". They return readings and alarm limits, and never "alarm breached". Facts are testable and the same on every call. Judgements belong to the agent, which can explain them.

**Keep one fixed output shape per tool.** Every Tiny Tank result has the same fields every time, with `null` where there is no value, plus `result_code` (`OK`, `NOT_FOUND`, `INVALID_INPUT`), a fixed `message` and a `source`. Clients map fields more reliably when the shape never changes.

**Date the data.** Include an `as_of` timestamp so the agent can say "as of 08:00" instead of presenting old data as live.

**Validate every argument as untrusted input,** exactly as you would a web form. The LLM writes the arguments, and the user, or text the LLM read elsewhere, can influence them. Use strict patterns (Tiny Tank accepts only ASCII `TK-[0-9]{3}`; Python's `\d` would also accept Arabic-Indic digits), ranges (`days` 1 to 7) and allowlists (site names).

**Never echo rejected input back.** Anything your server returns goes into the LLM's context. If you reply "TANK-102; ignore previous instructions is not a valid ID", you have delivered an attacker's text to the model. Return a fixed message instead. The SDK's own validation errors break this rule by default. The fix is in `MCP_Security.md`, rule R6.

**Avoid free-text arguments where you can.** A `symbol` restricted to known values is safe. A `query: str` that gets passed to SQL or to another system is a door. If a tool genuinely needs free text, it needs a security review of its own.

## 8. From the example to a real server

The Tiny Tank source shows the structure to copy:

```
src/tank_data.py        the data (in a real server: replaced by database or API calls)
src/business_logic.py   validation and lookups, with no MCP import, so it is unit-testable on its own
src/server.py           the MCP layer: tool registration, descriptions, logging, run options
tests/                  unit, protocol, and security tests
tools/                  live-endpoint checks: smoke test, security check, route comparison
```

Points worth copying from `src/server.py`:

- **Keep business logic separate from the MCP layer.** If you swap synthetic data for a database, only `business_logic.py` changes.
- **Write one structured log line per call:** timestamp, tool, a call ID, the validated subject (truncated), result code and duration. Never log headers, tokens or raw arguments.
- **Configure through environment variables** (host, port, allowed hosts and origins), so the same image runs locally and in every environment.
- **Raise `ToolError` for failures you expect.** Any other exception reaches the client as a generic "Error executing tool X" while the traceback stays in the server log. That is the SDK's default, and it's the right one.
- **`TinyTankServer` overrides `call_tool`** so that validation errors and unknown tool names never repeat caller input (see `MCP_Security.md`, rule R6).

## 9. The testing ladder

Run these in order. Each catches things the one before can't.

| Level | What | Tool in this package | Catches |
|---|---|---|---|
| 1 | Unit tests on business logic | `tests/test_business_logic.py` | Wrong data, validation gaps |
| 2 | In-process MCP tests | `tests/test_mcp_protocol.py` | Wrong schemas, registration mistakes, output shape |
| 3 | Security tests (white-box) | `tests/test_security.py` | Injection, reflection, side effects, transport, leakage |
| 4 | Live smoke test | `tools/smoke_test.py --url ...` | Hosting, TLS, path, and allowlist problems |
| 5 | Live security check (black-box) | `python -m tools.security_check --url ...` | What an agent actually sees through the real network path |
| 6 | Gateway parity | `tools/compare_routes.py direct.json gateway.json` | A gateway changing answers |
| 7 | Agent behaviour | Ask a real agent fixed questions and score the replies | Wrong tool choice, invented answers, overreach |

Levels 1 to 3 run in CI on every push. Levels 4 to 7 need a running server.

## 10. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `No module named 'mcp.server.fastmcp'` | Example written for SDK v1 | Use `from mcp.server.mcpserver import MCPServer` |
| HTTP 404 | Wrong path | The endpoint is `/mcp`, not `/` |
| HTTP 421 Misdirected Request | Host header not on the allowlist | Set `MCP_ALLOWED_HOSTS` to the public hostname |
| HTTP 403 "Invalid Origin header" | The client sends an Origin that isn't allowlisted (claude.ai sends `https://claude.ai`) | Add that client's origin to `MCP_ALLOWED_ORIGINS`. Never use `*` |
| `GET /mcp` hangs | GET opens a long-lived event stream | Use POST to test. Don't use `GET /mcp` as a health probe |
| Agent never calls your tool | The description doesn't match how users phrase things | Rewrite the description: what it returns, input format, example |
| Agent calls the tool with wrong arguments | Format not stated in the description | Add the format and an example to the description, and validate on the server |
| First call times out on a free host | The service was asleep | Call it once to wake it, or keep one instance running |
| Validation error text contains the user's input | SDK default behaviour | Apply rule R6 from `MCP_Security.md` |
