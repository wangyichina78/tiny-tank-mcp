"""Claude baseline for agent behaviour against a live Tiny Tank MCP endpoint.

The other tools check the server. This one checks what an agent does with it: whether it calls
get_tank_status when it should, answers only from the result, and handles NOT_FOUND and
INVALID_INPUT. Claude reaches the server through the Messages API MCP connector, so the
endpoint must be publicly reachable over HTTPS (a local 127.0.0.1 URL will not work).

Each case in tools/agent_eval_cases.json can run under two variants:
    bare        no system prompt: the tool description is all the agent gets
    instructed  system prompt = the server's own `instructions` text, fetched live
The gap between them shows how much the agent prompt has to carry, which is what an agent
builder on another platform needs to know.

    export ANTHROPIC_API_KEY=...
    python -m tools.agent_eval --url https://tiny-tank-mcp.onrender.com/mcp --out evidence/agent_eval.json

Two harnesses, same cases and scoring:
    --harness api          Messages API MCP connector. Needs ANTHROPIC_API_KEY and
                           `pip install -r requirements-eval.txt`; billed per token.
    --harness claude-code  headless `claude -p` with this server as its only tool. Runs on
                           whatever Claude Code is signed in with, including a Claude
                           subscription, so no API key is needed.

    python -m tools.agent_eval --harness claude-code --out evidence/agent_eval.json

Exit codes: 0 every check passed in every run of the instructed variant (bare is reported, not
gated), 1 a check failed, 2 transport, API, or setup error.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
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
# Claude Code's default system prompt is for coding; bare runs replace it with this neutral line.
NEUTRAL_SYSTEM = "You are a helpful assistant."
CC_TOOL = f"mcp__{SERVER_NAME}__{TOOL_NAME}"


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


class ApiHarness:
    """Messages API with the MCP connector: Anthropic's side connects to the server."""

    injects_server_instructions = None  # not documented; the bare variant measures it

    def __init__(self, url: str, model: str, effort: str):
        try:
            import anthropic
        except ImportError:
            raise SetupError("anthropic is not installed: pip install -r requirements-eval.txt") from None
        self.anthropic, self.client = anthropic, anthropic.Anthropic()
        self.url, self.model, self.effort = url, model, effort

    def _call(self, fn):
        try:
            return fn()
        except self.anthropic.APIError as e:
            raise SetupError(f"Claude API error: {e}") from None
        except TypeError as e:
            if "authentication" not in str(e):
                raise
            raise SetupError("No Anthropic credentials: set ANTHROPIC_API_KEY") from None

    def ask(self, prompt: str, system: str | None) -> dict:
        kwargs = {"system": system} if system else {}
        resp = self._call(lambda: self.client.beta.messages.create(
            model=self.model,
            max_tokens=16000,
            betas=BETAS,
            # A refused request is re-run on a fallback model; the served model is recorded per run.
            fallbacks="default",
            output_config={"effort": self.effort},
            mcp_servers=[{"type": "url", "url": self.url, "name": SERVER_NAME}],
            tools=[{"type": "mcp_toolset", "mcp_server_name": SERVER_NAME}],
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        ))
        return {
            "blocks": [b.to_dict() for b in resp.content],
            "served_model": resp.model,
            "refused": resp.stop_reason == "refusal",
            "detail": str(resp.stop_details) if resp.stop_reason == "refusal" else "",
        }

    def judge(self, rubric: str, prompt: str, reply: str) -> tuple[bool, str]:
        resp = self._call(lambda: self.client.messages.create(
            model=JUDGE_MODEL,
            max_tokens=256,
            output_config={"effort": "low"},
            messages=[{"role": "user", "content": judge_prompt(rubric, prompt, reply)}],
        ))
        return verdict("".join(b.text for b in resp.content if b.type == "text"))


class ClaudeCodeHarness:
    """Headless `claude -p` with this server as its only tool: the local CLI connects to it.

    Claude Code passes the server's `instructions` to the model even when the system prompt is
    replaced, so a bare run here is not bare. Only the instructed variant runs by default.
    """

    injects_server_instructions = True

    def __init__(self, url: str, model: str, effort: str, timeout: float = 300.0):
        self.model, self.effort, self.timeout = model, effort, timeout
        fd, self.mcp_config = tempfile.mkstemp(suffix=".json", prefix="tiny-tank-mcp-")
        with os.fdopen(fd, "w") as f:
            json.dump({"mcpServers": {SERVER_NAME: {"type": "http", "url": url}}}, f)

    def _claude(self, prompt: str, args: list[str]) -> list[dict]:
        # Prompt goes first: --tools and --allowedTools are variadic and would swallow it.
        cmd = ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose",
               "--no-session-persistence", "--setting-sources", "", *args]
        try:
            out = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                                 timeout=self.timeout)
        except FileNotFoundError:
            raise SetupError("claude CLI not found; install Claude Code and sign in") from None
        except subprocess.TimeoutExpired:
            raise SetupError(f"claude -p timed out after {self.timeout:.0f}s") from None
        events = []
        for line in out.stdout.splitlines():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        if not any(e.get("type") == "result" for e in events):
            raise SetupError(f"claude -p produced no result (exit {out.returncode}): {out.stderr.strip()[:300]}")
        return events

    def ask(self, prompt: str, system: str | None) -> dict:
        events = self._claude(prompt, [
            "--model", self.model, "--effort", self.effort,
            "--system-prompt", system or NEUTRAL_SYSTEM,
            "--strict-mcp-config", "--mcp-config", self.mcp_config,
            "--tools", "", "--allowedTools", CC_TOOL,
        ])
        blocks, served, result = [], None, {}
        for e in events:
            if e.get("type") == "system" and e.get("subtype") == "init":
                mcp = {s["name"]: s["status"] for s in e.get("mcp_servers", [])}
                if mcp.get(SERVER_NAME) != "connected":
                    raise SetupError(f"claude -p could not connect to the server: {mcp}")
            elif e.get("type") == "assistant":
                served = e["message"].get("model", served)
                for b in e["message"]["content"]:
                    if b["type"] == "tool_use" and b["name"] == CC_TOOL:
                        # Same shape the API harness returns, so extract() reads both.
                        blocks.append({"type": "mcp_tool_use", "name": TOOL_NAME, "input": b["input"]})
                    elif b["type"] == "text":
                        blocks.append(b)
            elif e.get("type") == "user":
                for b in e["message"].get("content", []):
                    if isinstance(b, dict) and b.get("type") == "tool_result":
                        blocks.append({"type": "mcp_tool_result", "is_error": b.get("is_error", False),
                                       "content": b.get("content")})
            elif e.get("type") == "result":
                result = e
        return {
            "blocks": blocks,
            "served_model": served,
            "refused": result.get("subtype") != "success",
            "detail": "" if result.get("subtype") == "success" else str(result.get("subtype")),
        }

    def judge(self, rubric: str, prompt: str, reply: str) -> tuple[bool, str]:
        events = self._claude(judge_prompt(rubric, prompt, reply),
                              ["--model", JUDGE_MODEL, "--tools", "", "--strict-mcp-config"])
        return verdict(next(e for e in events if e.get("type") == "result").get("result", ""))


def judge_prompt(rubric: str, prompt: str, reply: str) -> str:
    return (
        f"Grade an assistant reply against a rubric.\n\nRubric: {rubric}\n\n"
        f"User asked: {prompt}\n\nAssistant replied:\n{reply}\n\n"
        "Answer PASS or FAIL on the first line, then one sentence why."
    )


def verdict(out: str) -> tuple[bool, str]:
    out = out.strip()
    return out.upper().startswith("PASS"), out


HARNESSES = {"api": ApiHarness, "claude-code": ClaudeCodeHarness}


def run(url: str, harness_name: str, model: str, variants: list[str], runs: int, effort: str,
        timeout: float, only: list[str] | None = None) -> dict:
    cases = [c for c in load_cases() if not only or c["id"] in only]
    if not cases:
        raise SetupError(f"No cases match {only}")
    instructions = server_instructions(url, timeout)
    harness = HARNESSES[harness_name](url, model, effort)
    evidence: dict = {
        "url": url,
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "harness": harness_name,
        "client_injects_server_instructions": harness.injects_server_instructions,
        "agent_model": model,
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
                answer = harness.ask(case["prompt"], system)
                ids, results, text = extract(answer["blocks"])
                if answer["refused"]:
                    checks = [{"name": "no_answer", "pass": False, "detail": answer["detail"]}]
                else:
                    checks = score(case, ids, text, harness.judge)
                ok = all(c["pass"] for c in checks)
                passed += ok
                evidence["runs"].append({
                    "variant": variant, "case": case["id"], "run": n, "pass": ok,
                    "served_model": answer["served_model"],
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
    parser.add_argument("--harness", default="claude-code", choices=sorted(HARNESSES))
    parser.add_argument("--model", default=AGENT_MODEL)
    parser.add_argument("--out", help="Write JSON evidence to this file")
    parser.add_argument("--runs", type=int, default=3, help="Runs per case per variant (default 3)")
    parser.add_argument("--variants", help="bare and/or instructed (default: both for api, instructed for claude-code)")
    parser.add_argument("--cases", help="Comma-separated case IDs to run (default: all)")
    parser.add_argument("--effort", default="medium", choices=["low", "medium", "high", "xhigh", "max"])
    parser.add_argument("--timeout", type=float, default=90.0, help="Seconds; covers a cold start")
    args = parser.parse_args()
    default_variants = "instructed" if args.harness == "claude-code" else "bare,instructed"
    variants = [v.strip() for v in (args.variants or default_variants).split(",") if v.strip()]
    if not set(variants) <= {"bare", "instructed"}:
        parser.error("--variants takes bare and/or instructed")

    try:
        only = [c.strip() for c in args.cases.split(",")] if args.cases else None
        evidence = run(args.url, args.harness, args.model, variants, args.runs, args.effort, args.timeout, only)
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
