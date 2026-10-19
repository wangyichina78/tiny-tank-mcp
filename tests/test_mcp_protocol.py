"""Protocol tests against the real MCP SDK, using its in-process client."""

import json
import logging

import pytest

pytest.importorskip("mcp")

from mcp import Client  # noqa: E402

from src.server import mcp as server  # noqa: E402

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _call(tank_id):
    async with Client(server) as client:
        result = await client.call_tool("get_tank_status", {"tank_id": tank_id})
    assert not result.is_error
    return result.structured_content


EXPECTED_INPUTS = {
    "list_tanks": ({"site"}, []),
    "get_tank_status": ({"tank_id"}, ["tank_id"]),
    "get_inspection_history": ({"tank_id"}, ["tank_id"]),
    "get_tank_readings": ({"tank_id", "days"}, ["tank_id"]),
}


async def test_it01_discovery_four_tools_with_expected_inputs():
    async with Client(server) as client:
        tools = (await client.list_tools()).tools
    assert sorted(t.name for t in tools) == sorted(EXPECTED_INPUTS)
    for tool in tools:
        props, required = EXPECTED_INPUTS[tool.name]
        assert set(tool.input_schema["properties"]) == props
        assert tool.input_schema.get("required", []) == required
        assert tool.output_schema is not None
    status = next(t for t in tools if t.name == "get_tank_status")
    assert status.input_schema["properties"]["tank_id"]["type"] == "string"


async def _call_tool(name, arguments):
    async with Client(server) as client:
        result = await client.call_tool(name, arguments)
    assert not result.is_error
    return result.structured_content


async def test_new_tools_round_trip_over_mcp():
    assert (await _call_tool("list_tanks", {"site": "Site B"}))["count"] == 4
    history = await _call_tool("get_inspection_history", {"tank_id": "TK-105"})
    assert history["next_due"] == "2026-09-30" and history["as_of"] == "2026-10-16"
    readings = await _call_tool("get_tank_readings", {"tank_id": "TK-105", "days": 3})
    assert [r["level_pct"] for r in readings["readings"]] == [92.9, 93.7, 94.6]


@pytest.mark.parametrize(
    "tank_id,code,status",
    [
        ("TK-101", "OK", "In Service"),
        ("TK-102", "OK", "Inspection Due"),
        ("TK-103", "OK", "Out of Service"),
        ("TK-999", "NOT_FOUND", None),
        ("TANK-102", "INVALID_INPUT", None),
        ("", "INVALID_INPUT", None),
    ],
)
async def test_tool_calls(tank_id, code, status):
    r = await _call(tank_id)
    assert r["result_code"] == code
    assert r["status"] == status


async def test_it06_one_log_line_per_call_without_extra_fields(caplog):
    caplog.set_level(logging.INFO, logger="tiny_tank.calls")
    logger = logging.getLogger("tiny_tank.calls")
    logger.addHandler(caplog.handler)
    try:
        await _call("X" * 200)
    finally:
        logger.removeHandler(caplog.handler)
    lines = [json.loads(r.getMessage()) for r in caplog.records if r.name == "tiny_tank.calls"]
    assert len(lines) == 1
    line = lines[0]
    assert set(line) == {"ts", "event", "tool", "call_id", "tank_id", "result_code", "duration_ms"}
    assert len(line["tank_id"]) == 32
    assert line["result_code"] == "INVALID_INPUT"
