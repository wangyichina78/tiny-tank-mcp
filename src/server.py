"""Tiny Tank MCP server: one read-only tool, served over Streamable HTTP at /mcp."""

import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from mcp_types import CallToolResult, TextContent, ToolAnnotations

from src.business_logic import TankStatus, lookup_tank, normalize_tank_id

LOG_TANK_ID_MAX = 32

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

TOOL_ANNOTATIONS = ToolAnnotations(
    title="Get tank status (synthetic POC data)",
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

mcp = MCPServer(
    "tiny-tank",
    instructions=(
        "Use get_tank_status to look up a tank's status and site by tank ID (format TK-###). "
        "Answer only from the tool result and cite its source field. "
        "If result_code is INVALID_INPUT, ask the user for a valid ID. "
        "If result_code is NOT_FOUND, say the tank was not found."
    ),
)


def _log_call(call_id: str, tank_id: str, result_code: str, started: float) -> None:
    logger.info(
        json.dumps(
            {
                "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                "event": "tool_call",
                "tool": "get_tank_status",
                "call_id": call_id,
                "tank_id": tank_id[:LOG_TANK_ID_MAX],
                "result_code": result_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 3),
            }
        )
    )


@mcp.tool(annotations=TOOL_ANNOTATIONS, meta={SECURITY_META_KEY: SECURITY_DECLARATION})
def get_tank_status(tank_id: str) -> TankStatus:
    """Return status and site for a tank by its ID (format TK-###, for example TK-102).

    Read-only lookup against a synthetic POC dataset. result_code is OK, NOT_FOUND, or INVALID_INPUT.
    """
    call_id = uuid.uuid4().hex
    started = time.perf_counter()
    result_code = "ERROR"
    try:
        result = lookup_tank(tank_id)
        result_code = result["result_code"]
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(result, indent=2))],
            structured_content=dict(result),
            meta={SECURITY_META_KEY: SECURITY_DECLARATION},
        )
    finally:
        _log_call(call_id, normalize_tank_id(tank_id), result_code, started)


def _csv_env(name: str) -> list[str]:
    return [item.strip() for item in os.environ.get(name, "").split(",") if item.strip()]


def run_options() -> dict:
    """Streamable HTTP options. Defaults: 127.0.0.1:8000/mcp, stateless, JSON responses."""
    options: dict = {
        "host": os.environ.get("MCP_HOST", "127.0.0.1"),
        "port": int(os.environ.get("MCP_PORT", "8000")),
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
