"""Tiny Tank MCP server: four read-only tools, served over Streamable HTTP at /mcp."""

import json
import logging
import os
import sys
import time
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError, UnexpectedToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp_types import CallToolResult, TextContent, ToolAnnotations
from pydantic import ValidationError

from src.business_logic import (
    MAX_READING_DAYS,
    InspectionHistory,
    TankList,
    TankReadings,
    TankStatus,
    inspection_history,
    list_tanks as list_tank_records,
    lookup_tank,
    normalize_tank_id,
    tank_readings,
)

LOG_SUBJECT_MAX = 32

SECURITY_META_KEY = "tinytank/security-declaration"

# Self-declared by this server. A calling agent should verify it against independent test
# evidence (docs/security_test_cadence.md), not trust it on its own.
SECURITY_DECLARATION = {
    "declaration_version": "1.0",
    "read_only": True,
    "side_effects": "none",
    "data_classification": "synthetic-test-data",
    "network_egress": False,
    "filesystem_access": False,
    "code_execution": False,
    "reflects_caller_input": False,
    "instructions_in_output": False,
    "authentication": "none (public test endpoint, synthetic data only)",
    "verified_by": "SEC-01..SEC-05",
}

# Descriptions are explicit strings, not docstrings: docstring indentation handling differs between
# Python versions, which would change the tool definitions an agent sees (and the SEC-01 manifest hash).
TOOL_DESCRIPTIONS = {
    "list_tanks": (
        "List tanks in the synthetic POC dataset: tank ID, site, product and capacity in barrels. "
        "Optionally filter by site (Site A or Site B). Use the tank IDs with the other tools."
    ),
    "get_tank_status": (
        "Return status and site for a tank by its ID (format TK-###, for example TK-102). "
        "Read-only lookup against a synthetic POC dataset. result_code is OK, NOT_FOUND, or INVALID_INPUT."
    ),
    "get_inspection_history": (
        "Return the inspection history of a tank by its ID (format TK-###): date, type, result and notes "
        "of each inspection, newest first, and the next due date. next_due is null while a tank awaits repair. "
        "Compare next_due with as_of, the date of the data snapshot."
    ),
    "get_tank_readings": (
        f"Return daily level and temperature readings for a tank by its ID (format TK-###) for the last "
        f"1 to {MAX_READING_DAYS} days (default {MAX_READING_DAYS}), oldest first, with the tank's high and low "
        "level alarm limits. Levels are percent of capacity, temperatures in degrees F."
    ),
}


def _annotations(title: str) -> ToolAnnotations:
    return ToolAnnotations(
        title=title,
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    )


logger = logging.getLogger("tiny_tank.calls")
if not logger.handlers:
    _handler = logging.StreamHandler(sys.stderr)
    _handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


class TinyTankServer(MCPServer):
    """MCPServer that never reflects caller input in error results.

    The SDK's argument-validation errors include the rejected value (`input_value=...`) and an unknown
    tool name is echoed back, so caller text would reach the agent's context. Both are replaced with
    server-authored text naming only the field and what it expected.
    """

    async def call_tool(self, name: str, arguments: dict[str, Any], context=None):
        tools = {t.name: t for t in await self.list_tools()}
        if name not in tools:
            raise ToolError("Unknown tool. Call tools/list for the available tools.")
        try:
            return await super().call_tool(name, arguments, context)
        except UnexpectedToolError:
            raise
        except ToolError as exc:
            cause = exc.__cause__
            if not isinstance(cause, ValidationError):
                raise
            params = set((tools[name].input_schema or {}).get("properties", {}))
            problems = sorted(
                {
                    f"{e['loc'][0] if e['loc'] and e['loc'][0] in params else 'arguments'}: {e['msg']}"
                    for e in cause.errors(include_input=False, include_url=False)
                }
            )
            raise ToolError(f"Error executing tool {name}: invalid arguments ({'; '.join(problems)})") from cause


mcp = TinyTankServer(
    "tiny-tank",
    instructions=(
        "Tools for a synthetic tank dataset: list_tanks, get_tank_status, get_inspection_history and "
        "get_tank_readings. Combine them when a question needs more than one fact. All data is a snapshot "
        "dated as_of; treat as_of as today. Answer only from tool results and say which tool each fact came "
        "from. If result_code is INVALID_INPUT, ask the user for valid input. If result_code is NOT_FOUND, "
        "say the tank was not found."
    ),
)


def _log_call(tool: str, call_id: str, subject_key: str, subject: str, result_code: str, started: float) -> None:
    logger.info(
        json.dumps(
            {
                "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                "event": "tool_call",
                "tool": tool,
                "call_id": call_id,
                subject_key: subject[:LOG_SUBJECT_MAX],
                "result_code": result_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 3),
            }
        )
    )


def _respond(tool: str, subject_key: str, subject: str, compute: Callable[[], dict]) -> CallToolResult:
    """Run one lookup, wrap it with the security declaration, and write one log line."""
    call_id = uuid.uuid4().hex
    started = time.perf_counter()
    result_code = "ERROR"
    try:
        result = compute()
        result_code = result["result_code"]
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(result, indent=2))],
            structured_content=dict(result),
            meta={SECURITY_META_KEY: SECURITY_DECLARATION},
        )
    finally:
        _log_call(tool, call_id, subject_key, subject, result_code, started)


def _tool(name: str, title: str):
    return mcp.tool(
        name=name,
        description=TOOL_DESCRIPTIONS[name],
        annotations=_annotations(title),
        meta={SECURITY_META_KEY: SECURITY_DECLARATION},
    )


@_tool("list_tanks", "List tanks (synthetic POC data)")
def list_tanks(site: str | None = None) -> TankList:
    """See TOOL_DESCRIPTIONS; that string is what agents see."""
    subject = " ".join(site.split()) if isinstance(site, str) else ""
    return _respond("list_tanks", "site", subject, lambda: list_tank_records(site))


@_tool("get_tank_status", "Get tank status (synthetic POC data)")
def get_tank_status(tank_id: str) -> TankStatus:
    """See TOOL_DESCRIPTIONS; that string is what agents see."""
    return _respond("get_tank_status", "tank_id", normalize_tank_id(tank_id), lambda: lookup_tank(tank_id))


@_tool("get_inspection_history", "Get inspection history (synthetic POC data)")
def get_inspection_history(tank_id: str) -> InspectionHistory:
    """See TOOL_DESCRIPTIONS; that string is what agents see."""
    return _respond(
        "get_inspection_history", "tank_id", normalize_tank_id(tank_id), lambda: inspection_history(tank_id)
    )


@_tool("get_tank_readings", "Get tank readings (synthetic POC data)")
def get_tank_readings(tank_id: str, days: int = MAX_READING_DAYS) -> TankReadings:
    """See TOOL_DESCRIPTIONS; that string is what agents see."""
    return _respond(
        "get_tank_readings", "tank_id", normalize_tank_id(tank_id), lambda: tank_readings(tank_id, days)
    )


def _csv_env(name: str) -> list[str]:
    return [item.strip() for item in os.environ.get(name, "").split(",") if item.strip()]


def run_options() -> dict:
    """Streamable HTTP options. Defaults: 127.0.0.1:8000/mcp, stateless, JSON responses."""
    options: dict = {
        "host": os.environ.get("MCP_HOST", "127.0.0.1"),
        # PORT is the convention hosting platforms (Render, Cloud Run, Heroku) use to assign a port.
        "port": int(os.environ.get("MCP_PORT") or os.environ.get("PORT") or "8000"),
        "streamable_http_path": "/mcp",
        "stateless_http": True,
        "json_response": True,
    }
    allowed_hosts = _csv_env("MCP_ALLOWED_HOSTS")
    allowed_origins = _csv_env("MCP_ALLOWED_ORIGINS")
    if allowed_hosts or allowed_origins:
        options["transport_security"] = TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=allowed_hosts,
            allowed_origins=allowed_origins,
        )
    return options


def main() -> None:
    mcp.run(transport="streamable-http", **run_options())


if __name__ == "__main__":
    main()
