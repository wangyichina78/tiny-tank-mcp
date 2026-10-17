"""Claude baseline for agent behaviour against a live Tiny Tank MCP endpoint.

The other tools check the server. This one checks what an agent does with it: whether it calls
get_tank_status when it should, answers only from the result, and handles NOT_FOUND and
INVALID_INPUT. Claude reaches the server through the Messages API MCP connector, so the
endpoint must be publicly reachable over HTTPS (a local 127.0.0.1 URL will not work).

Each case in tools/agent_eval_cases.json runs under two variants:
    bare        no system prompt: the tool description is all the agent gets
    instructed  system prompt = the server's own `instructions` text, fetched live
The gap between them shows how much the agent prompt has to carry, which is what an agent
builder on another platform needs to know.

    export ANTHROPIC_API_KEY=...
    python -m tools.agent_eval --url https://tiny-tank-mcp.onrender.com/mcp --out evidence/agent_eval.json

Needs `pip install -r requirements-eval.txt`. Every run calls the Claude API and costs money.

Exit codes: 0 every check passed in every run of the instructed variant (bare is reported, not
gated), 1 a check failed, 2 transport, API, or setup error.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from tools.smoke_test import CLIENT_PROTOCOL, Session, TransportError

CASES_FILE = Path(__file__).resolve().parent / "agent_eval_cases.json"
SERVER_NAME = "tiny-tank"
TOOL_NAME = "get_tank_status"
AGENT_MODEL = "claude-opus-5-5"
JUDGE_MODEL = "claude-haiku-5-5"
BETAS = ["mcp-client-2025-11-20", "server-side-fallback-2026-07-01"]
SOURCE_MARKERS = ("synthetic", "tiny tank")


class SetupError(Exception):
    pass


def load_cases(path: Path = CASES_FILE) -> list[dict]:
    return json.loads(path.read_text())["cases"]


def server_instructions(url: str, timeout: float) -> str:
    """Wake the server (free hosts sleep) and return its initialize `instructions`."""
    s = Session(url, timeout)
    init = s.request(
        "initialize",
        {
            "protocolVersion": CLIENT_PROTOCOL,
            "capabilities": {},
            "clientInfo": {"name": "tiny-tank-agent-eval", "version": "1.0"},
        },
    )
    instructions = init.get("instructions")
    if not instructions:
        raise SetupError("Server returned no instructions; the instructed variant needs them")
    return instructions


def extract(blocks: list[dict]) -> tuple[list[str], list[dict], str]:
    """Return (tank IDs the tool was called with, tool results, reply text) from response blocks."""
    ids, results, text = [], [], []
    for b in blocks:
        if b.get("type") == "mcp_tool_use" and b.get("name") == TOOL_NAME:
            ids.append(str((b.get("input") or {}).get("tank_id", "")))
        elif b.get("type") == "mcp_tool_result":
            results.append({"is_error": b.get("is_error", False), "content": b.get("content")})
        elif b.get("type") == "text":
            text.append(b.get("text", ""))
    return ids, results, "\n".join(text).strip()


def score(case: dict, ids: list[str], text: str, judge=None) -> list[dict]:
    """Apply a case's checks to one run. `judge(rubric, prompt, reply)` returns (bool, reason)."""
    checks = []
    low = text.lower()

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"name": name, "pass": ok, "detail": detail})

    if "expect_tool" in case:
        called = bool(ids)
        check("tool_called" if case["expect_tool"] else "tool_not_called",
              called == case["expect_tool"], f"calls={ids}")
    if case.get("expect_ids"):
        got = {i.strip().upper() for i in ids}
        missing = [i for i in case["expect_ids"] if i.upper() not in got]
        check("tool_args", not missing, f"missing {missing}" if missing else "")
    for phrase in case.get("must_contain", []):
        check(f"contains:{phrase}", phrase.lower() in low)
    if case.get("contain_any"):
        check("contains_any", any(p.lower() in low for p in case["contain_any"]))
    for phrase in case.get("must_not_contain", []):
        check(f"not_contains:{phrase}", phrase.lower() not in low)
    if case.get("cites_source"):
        check("cites_source", any(m in low for m in SOURCE_MARKERS))
    if case.get("judge"):
        if judge is None:
            check("judge", False, "no judge available")
        else:
            ok, reason = judge(case["judge"], case["prompt"], text)
            check("judge", ok, reason)
    return checks


def make_client():
    try:
        import anthropic
    except ImportError:
        raise SetupError("anthropic is not installed: pip install -r requirements-eval.txt") from None
    return anthropic, anthropic.Anthropic()


def ask_agent(client, url: str, prompt: str, system: str | None, effort: str):
    kwargs = {}
    if system:
        kwargs["system"] = system
    return client.beta.messages.create(
        model=AGENT_MODEL,
        max_tokens=16000,
        betas=BETAS,
        # A refused request is re-run on a fallback model; the served model is recorded per run.
        fallbacks="default",
        output_config={"effort": effort},
        mcp_servers=[{"type": "url", "url": url, "name": SERVER_NAME}],
        tools=[{"type": "mcp_toolset", "mcp_server_name": SERVER_NAME}],
        messages=[{"role": "user", "content": prompt}],
        **kwargs,
    )


def make_judge(client):
    def judge(rubric: str, prompt: str, reply: str) -> tuple[bool, str]:
        resp = client.messages.create(
            model=JUDGE_MODEL,
            max_tokens=256,
            output_config={"effort": "low"},
            messages=[{
                "role": "user",
                "content": (
                    f"Grade an assistant reply against a rubric.\n\nRubric: {rubric}\n\n"
                    f"User asked: {prompt}\n\nAssistant replied:\n{reply}\n\n"
                    "Answer PASS or FAIL on the first line, then one sentence why."
                ),
            }],
        )
        out = "".join(b.text for b in resp.content if b.type == "text").strip()
        return out.upper().startswith("PASS"), out
    return judge


def run(url: str, variants: list[str], runs: int, effort: str, timeout: float) -> dict:
    instructions = server_instructions(url, timeout)
    anthropic, client = make_client()
    judge = make_judge(client)
    cases = load_cases()
    evidence: dict = {
        "url": url,
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "agent_model": AGENT_MODEL,
        "judge_model": JUDGE_MODEL,
        "effort": effort,
        "server_instructions": instructions,
        "runs_per_case": runs,
        "summary": {},
        "runs": [],
    }

    for variant in variants:
        system = instructions if variant == "instructed" else None
        summary = evidence["summary"][variant] = {}
        for case in cases:
            passed = 0
            for n in range(1, runs + 1):
                try:
                    resp = ask_agent(client, url, case["prompt"], system, effort)
                except anthropic.APIError as e:
                    raise SetupError(f"Claude API error on {case['id']}: {e}") from None
                except TypeError as e:
                    if "authentication" not in str(e):
                        raise
                    raise SetupError("No Anthropic credentials: set ANTHROPIC_API_KEY") from None
                blocks = [b.to_dict() for b in resp.content]
                ids, results, text = extract(blocks)
                if resp.stop_reason == "refusal":
                    checks = [{"name": "refusal", "pass": False, "detail": str(resp.stop_details)}]
                else:
                    checks = score(case, ids, text, judge)
                ok = all(c["pass"] for c in checks)
                passed += ok
                evidence["runs"].append({
                    "variant": variant, "case": case["id"], "run": n, "pass": ok,
                    "served_model": resp.model, "stop_reason": resp.stop_reason,
                    "tool_calls": ids, "tool_results": results, "reply": text, "checks": checks,
                })
                failed = [c["name"] for c in checks if not c["pass"]]
                print(f"[{'PASS' if ok else 'FAIL'}] {variant:<10} {case['id']:<26} run {n}"
                      f"{' - failed ' + ', '.join(failed) if failed else ''}")
            summary[case["id"]] = f"{passed}/{runs}"

    gated = [r for r in evidence["runs"] if r["variant"] == "instructed"]
    evidence["all_pass"] = bool(gated) and all(r["pass"] for r in gated)
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default="https://tiny-tank-mcp.onrender.com/mcp")
    parser.add_argument("--out", help="Write JSON evidence to this file")
    parser.add_argument("--runs", type=int, default=3, help="Runs per case per variant (default 3)")
    parser.add_argument("--variants", default="bare,instructed")
    parser.add_argument("--effort", default="medium", choices=["low", "medium", "high", "xhigh", "max"])
    parser.add_argument("--timeout", type=float, default=90.0, help="Seconds; covers a cold start")
    args = parser.parse_args()
    variants = [v.strip() for v in args.variants.split(",") if v.strip()]
    if not set(variants) <= {"bare", "instructed"}:
        parser.error("--variants takes bare and/or instructed")

    try:
        evidence = run(args.url, variants, args.runs, args.effort, args.timeout)
    except (TransportError, SetupError) as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 2

    print("\nPass rate per case:")
    for variant, summary in evidence["summary"].items():
        print(f"  {variant}: " + ", ".join(f"{k} {v}" for k, v in summary.items()))
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w") as f:
            json.dump(evidence, f, indent=2)
        print(f"Evidence written to {args.out}")
    if "instructed" not in variants:
        print("Instructed variant not run: nothing gated")
        return 0
    print("ALL PASS" if evidence["all_pass"] else "FAILURES PRESENT")
    return 0 if evidence["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
