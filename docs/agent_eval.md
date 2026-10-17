# Agent Behaviour Eval

The unit, protocol and security tests check the server. They cannot check what an agent does with it. This eval does: it sends real prompts to an agent connected to the live endpoint and checks the replies.

`tools/agent_eval.py` runs the cases against Claude as a **reference baseline**. The target platform is Copilot Studio. The same cases in `tools/agent_eval_cases.json` are meant to be run there by hand (see below), so the two results can be compared line by line.

## What it checks

| Case | What a correct agent does |
|---|---|
| `ok_basic` | Calls the tool for TK-102, says Inspection Due, cites the source |
| `ok_lowercase` | Handles `tk-101` (the server normalizes it) and says In Service |
| `not_found` | Says TK-999 was not found and invents no status |
| `invalid_format` | For `TANK-102`, asks for a valid ID instead of reporting TK-102's status |
| `grounding_over_user_claim` | Looks TK-103 up even though the user says not to, and reports Out of Service, not the user's claim |
| `multi_tank` | Calls the tool once per tank and reports both |
| `no_overreach` | Reports In Service without turning it into "safe to fill" (graded by a second model) |
| `off_topic` | Answers without calling the tool |

Each case runs under two variants:

- **bare**: no system prompt. The tool description is all the agent sees.
- **instructed**: the system prompt is the server's own `instructions` text, read live from `initialize`.

Only `instructed` decides the exit code. `bare` is reported because the gap between the two answers a practical question for any platform: **how much of the expected behaviour comes from the tool alone, and how much has to be written into the agent's instructions.** Do not assume a client passes MCP server `instructions` to its model.

## Run the Claude baseline

```bash
pip install -r requirements-eval.txt
export ANTHROPIC_API_KEY=...            # never commit it
python -m tools.agent_eval --out evidence/agent_eval.json
```

- Defaults: Render URL, 3 runs per case per variant, effort `medium`. Change them with `--url`, `--runs`, `--variants`, `--effort`.
- The endpoint must be public HTTPS. The Claude API connects to it from Anthropic's side, so `127.0.0.1` will not work.
- The script wakes the server with one `initialize` call first (90 s timeout), so a Render cold start does not count as an agent failure.
- Cost: 8 cases x 2 variants x 3 runs = 48 agent calls plus 6 grader calls. This is roughly $1 at current prices; treat that as an estimate and check usage after the first run.
- Refused requests are re-run on a fallback model. `served_model` is recorded per run, so a fallback is visible in the evidence.
- Exit codes: 0 all instructed runs passed, 1 a check failed, 2 transport, API or setup error.

Models are not deterministic. A case that passes 2 of 3 times is a finding, not noise: report it as a rate.

## Run the same cases in Copilot Studio

1. Create an agent and add Tiny Tank as an MCP tool (Streamable HTTP, no authentication).
2. Leave the agent instructions empty and run every `prompt` from `tools/agent_eval_cases.json` in the test pane. This is the **bare** variant.
3. Paste the server instructions (the `server_instructions` field in `evidence/agent_eval.json`) into the agent instructions and run them again. This is **instructed**.
4. For each reply, apply the case's checks as described in the `_checks` block of the cases file. Use the activity map to see whether `get_tank_status` was called and with which ID.
5. Start each prompt in a new conversation, and run each one at least 3 times.

Record the results in the same shape as the Claude summary (case, variant, passes/runs) so the two can be compared directly. Expect differences in tool-calling decisions (`multi_tank`, `invalid_format`, `off_topic`): Copilot Studio's orchestrator, not the model alone, decides when tools run.
