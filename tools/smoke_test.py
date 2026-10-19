"""Smoke test a live Tiny Tank MCP endpoint using only the standard library.

Runs initialize, tools/list, and seven tool calls, then writes a JSON evidence file.

    python tools/smoke_test.py --url http://127.0.0.1:8000/mcp --out evidence/direct.json

Optional gateway credential, read from the environment only (never printed or saved):
    MCP_GATEWAY_AUTH_HEADER  header name, e.g. Ocp-Apim-Subscription-Key or Authorization
    MCP_GATEWAY_AUTH_VALUE   header value

Exit codes: 0 all checks pass, 1 a check failed, 2 transport or HTTP error.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

CLIENT_PROTOCOL = "2025-06-18"

EXPECTED_TOOLS = ["get_inspection_history", "get_tank_readings", "get_tank_status", "list_tanks"]

# (tool, arguments, expected result fields). Includes the two planted inconsistencies (TK-105, TK-107).
EXPECTED_CALLS = [
    ("get_tank_status", {"tank_id": "TK-101"}, {"result_code": "OK", "status": "In Service", "site": "Site A"}),
    ("get_tank_status", {"tank_id": "TK-102"}, {"result_code": "OK", "status": "Inspection Due", "site": "Site A"}),
    ("get_tank_status", {"tank_id": "TK-103"}, {"result_code": "OK", "status": "Out of Service", "site": "Site A"}),
    ("get_tank_status", {"tank_id": "TK-105"}, {"result_code": "OK", "status": "In Service", "site": "Site B"}),
    ("get_tank_status", {"tank_id": "TK-999"}, {"result_code": "NOT_FOUND", "status": None, "site": None}),
    ("get_tank_status", {"tank_id": "TANK-102"}, {"result_code": "INVALID_INPUT", "status": None, "site": None}),
    ("get_tank_status", {"tank_id": "tk-102"}, {"result_code": "OK", "status": "Inspection Due", "site": "Site A"}),
    ("get_tank_status", {"tank_id": ""}, {"result_code": "INVALID_INPUT", "status": None, "site": None}),
    ("list_tanks", {}, {"result_code": "OK", "count": 8}),
    ("list_tanks", {"site": "Site B"}, {"result_code": "OK", "count": 4, "site": "Site B"}),
    ("list_tanks", {"site": "Site Z"}, {"result_code": "INVALID_INPUT", "count": 0}),
    ("get_inspection_history", {"tank_id": "TK-105"}, {"result_code": "OK", "next_due": "2026-09-30", "as_of": "2026-10-16"}),
    ("get_inspection_history", {"tank_id": "TK-107"}, {"result_code": "OK", "next_due": None}),
    ("get_tank_readings", {"tank_id": "TK-105", "days": 3}, {"result_code": "OK", "days": 3, "high_alarm_pct": 90.0}),
    ("get_tank_readings", {"tank_id": "TK-107"}, {"result_code": "OK", "days": 7}),
    ("get_tank_readings", {"tank_id": "TK-105", "days": 0}, {"result_code": "INVALID_INPUT"}),
]


class TransportError(Exception):
    pass


class Session:
    def __init__(self, url: str, timeout: float):
        self.url = url
        self.timeout = timeout
        self.next_id = 1
        self.protocol: str | None = None
        self.session_id: str | None = None
        self.auth_header = os.environ.get("MCP_GATEWAY_AUTH_HEADER")
        self.auth_value = os.environ.get("MCP_GATEWAY_AUTH_VALUE")

    def _headers(self) -> dict:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.protocol:
            headers["MCP-Protocol-Version"] = self.protocol
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        if self.auth_header and self.auth_value:
            headers[self.auth_header] = self.auth_value
        return headers

    def _post(self, payload: dict) -> tuple[int, dict | None]:
        req = urllib.request.Request(
            self.url, data=json.dumps(payload).encode(), headers=self._headers(), method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                sid = resp.headers.get("Mcp-Session-Id")
                if sid:
                    self.session_id = sid
                body = resp.read().decode()
                ctype = resp.headers.get("Content-Type", "")
                return resp.status, _parse_body(body, ctype) if body else None
        except urllib.error.HTTPError as e:
            raise TransportError(f"HTTP {e.code} from {self.url}") from None
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            raise TransportError(f"Cannot reach {self.url}: {e}") from None

    def request(self, method: str, params: dict) -> dict:
        payload = {"jsonrpc": "2.0", "id": self.next_id, "method": method, "params": params}
        self.next_id += 1
        _, msg = self._post(payload)
        if msg is None:
            raise TransportError(f"Empty response to {method}")
        if "error" in msg:
            raise TransportError(f"{method} returned JSON-RPC error {msg['error']}")
        return msg["result"]

    def notify(self, method: str) -> None:
        self._post({"jsonrpc": "2.0", "method": method})


def _parse_body(body: str, ctype: str) -> dict:
    if "text/event-stream" in ctype:
        for line in body.splitlines():
            if line.startswith("data:"):
                msg = json.loads(line[5:].strip())
                if "result" in msg or "error" in msg:
                    return msg
        raise TransportError("No JSON-RPC response in event stream")
    return json.loads(body)


def run(url: str, timeout: float) -> dict:
    s = Session(url, timeout)
    evidence: dict = {
        "url": url,
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "checks": [],
        "calls": [],
    }

    def check(name: str, ok: bool, detail: str = "") -> None:
        evidence["checks"].append({"name": name, "pass": ok, "detail": detail})
        print(f"[{'PASS' if ok else 'FAIL'}] {name}{' - ' + detail if detail else ''}")

    init = s.request(
        "initialize",
        {
            "protocolVersion": CLIENT_PROTOCOL,
            "capabilities": {},
            "clientInfo": {"name": "tiny-tank-smoke-test", "version": "1.0"},
        },
    )
    s.protocol = init.get("protocolVersion", CLIENT_PROTOCOL)
    s.notify("notifications/initialized")
    evidence["server_info"] = init.get("serverInfo")
    evidence["protocol_version"] = s.protocol
    check("initialize", "capabilities" in init, f"protocol {s.protocol}")

    tools = s.request("tools/list", {}).get("tools", [])
    names = sorted(t["name"] for t in tools)
    check("tools/list exposes the four read-only tools", names == EXPECTED_TOOLS, f"tools={names}")

    for tool, arguments, expected in EXPECTED_CALLS:
        result = s.request("tools/call", {"name": tool, "arguments": arguments})
        data = result.get("structuredContent")
        if data is None and result.get("content"):
            data = json.loads(result["content"][0]["text"])
        evidence["calls"].append({"tool": tool, "input": arguments, "is_error": result.get("isError", False), "result": data})
        got = {k: (data or {}).get(k) for k in expected}
        ok = not result.get("isError") and got == expected
        check(f"{tool}({json.dumps(arguments)}) -> {expected['result_code']}", ok, "" if ok else f"got {got}")

    evidence["all_pass"] = all(c["pass"] for c in evidence["checks"])
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default="http://127.0.0.1:8000/mcp")
    parser.add_argument("--out", help="Write JSON evidence to this file")
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()

    try:
        evidence = run(args.url, args.timeout)
    except TransportError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 2

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w") as f:
            json.dump(evidence, f, indent=2)
        print(f"Evidence written to {args.out}")
    print("ALL PASS" if evidence["all_pass"] else "FAILURES PRESENT")
    return 0 if evidence["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
