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

EXPECTED = [
    ("TK-101", "OK", "In Service", "Site A"),
    ("TK-102", "OK", "Inspection Due", "Site A"),
    ("TK-103", "OK", "Out of Service", "Site A"),
    ("TK-999", "NOT_FOUND", None, None),
    ("TANK-102", "INVALID_INPUT", None, None),
    ("tk-102", "OK", "Inspection Due", "Site A"),
    ("", "INVALID_INPUT", None, None),
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
    names = [t["name"] for t in tools]
    props = tools[0].get("inputSchema", {}).get("properties", {}) if tools else {}
    check(
        "tools/list exposes get_tank_status with one string input tank_id",
        names == ["get_tank_status"] and list(props) == ["tank_id"] and props["tank_id"].get("type") == "string",
        f"tools={names}",
    )

    for tank_id, code, status, site in EXPECTED:
        result = s.request("tools/call", {"name": "get_tank_status", "arguments": {"tank_id": tank_id}})
        data = result.get("structuredContent")
        if data is None and result.get("content"):
            data = json.loads(result["content"][0]["text"])
        evidence["calls"].append({"input": tank_id, "is_error": result.get("isError", False), "result": data})
        ok = (
            not result.get("isError")
            and data is not None
            and (data.get("result_code"), data.get("status"), data.get("site")) == (code, status, site)
        )
        check(f"get_tank_status({tank_id!r}) -> {code}", ok, f"got {data and data.get('result_code')}")

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
