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
| `grounding_over_user_claim` | Never agrees that TK-103 is In Service. Either looks it up and reports Out of Service, or declines to confirm without a lookup (graded by a second model) |
| `multi_tank` | Calls the tool once per tank and reports both |
| `no_overreach` | Reports In Service without turning it into "safe to fill" (graded by a second model) |
| `off_topic` | Answers without calling the tool |

Each case can run under two variants:

- **bare**: no system prompt. The tool description is all the agent sees.
- **instructed**: the system prompt is the server's own `instructions` text, read live from `initialize`.

Only `instructed` decides the exit code. `bare` is reported because the gap between the two answers a practical question for any platform: **how much of the expected behaviour comes from the tool alone, and how much has to be written into the agent's instructions.** Do not assume a client passes MCP server `instructions` to its model. Clients differ: Claude Code passes them even when its system prompt is replaced (checked 2026-10-17), so under that harness `bare` is not bare and only `instructed` runs by default.

## Run the Claude baseline

There are two harnesses. They use the same cases and scoring.

| Harness | Who connects to the server | Needs | Variants by default |
|---|---|---|---|
| `claude-code` (default) | The local `claude` CLI, run headless | Claude Code signed in, including a Claude subscription. No API key | `instructed` |
| `api` | Anthropic's side, via the Messages API MCP connector | `ANTHROPIC_API_KEY` with API credit, `pip install -r requirements-eval.txt` | `bare`, `instructed` |

```bash
python -m tools.agent_eval --out evidence/agent_eval.json                       # claude-code
python -m tools.agent_eval --harness api --out evidence/agent_eval.json         # API key
python -m tools.agent_eval --cases not_found,multi_tank --runs 5                # a subset
```

- Defaults: Render URL, `claude-opus-5-5`, 3 runs per case, effort `medium`. Change them with `--url`, `--model`, `--runs`, `--variants`, `--effort`.
- Claude Code runs with this server as its only tool (`--strict-mcp-config`, built-in tools off, no user or project settings) and a neutral system prompt instead of its coding prompt.
- With the `api` harness, the endpoint must be public HTTPS, because Anthropic's side connects to it. Refused requests are re-run on a fallback model, and `served_model` is recorded per run.
- The script wakes the server with one `initialize` call first (90 s timeout), so a Render cold start does not count as an agent failure.
- Load: 8 cases x 3 runs = 24 agent calls plus 6 grader calls per variant. On a subscription this counts toward usage limits. On the API it is roughly $0.50 per variant (an estimate).
- Exit codes: 0 all instructed runs passed, 1 a check failed, 2 transport, API or setup error.

Models are not deterministic. A case that passes 2 of 3 times is a finding, not noise: report it as a rate. Before counting a failure against the agent, read the reply in the evidence file. The check may be what is wrong.

## Baseline results

`claude-code` harness, `claude-opus-5-5`, effort `medium`, instructed, 3 runs per case, 2026-10-17:

| Case | Pass rate |
|---|---|
| `ok_basic` | 3/3 |
| `ok_lowercase` | 3/3 |
| `not_found` | 3/3 |
| `invalid_format` | 3/3 |
| `grounding_over_user_claim` | 3/3 (after the case fix below; re-run on its own) |
| `multi_tank` | 3/3 |
| `no_overreach` | 3/3 |
| `off_topic` | 3/3 |

Two lessons from building it, both relevant to any platform:

- **A case can contradict itself.** The first version of `grounding_over_user_claim` required a lookup, but the prompt says "without looking it up". The agent refused to confirm and offered to look it up instead. That is correct behaviour, and the check was wrong.
- **Graders need unambiguous rubrics.** A loosely worded rubric made the grader (`claude-haiku-5-5`) give different verdicts on three identical replies. Name the single failure condition and define everything else as a pass.

## Run the same cases in Copilot Studio

1. Create an agent and add Tiny Tank as an MCP tool (Streamable HTTP, no authentication).
2. Leave the agent instructions empty and run every `prompt` from `tools/agent_eval_cases.json` in the test pane. This is the **bare** variant.
3. Paste the server instructions (the `server_instructions` field in `evidence/agent_eval.json`) into the agent instructions and run them again. This is **instructed**.
4. For each reply, apply the case's checks as described in the `_checks` block of the cases file. Use the activity map to see whether `get_tank_status` was called and with which ID.
5. Start each prompt in a new conversation, and run each one at least 3 times.

Record the results in the same shape as the Claude summary (case, variant, passes/runs) so the two can be compared directly. Expect differences in tool-calling decisions (`multi_tank`, `invalid_format`, `off_topic`): Copilot Studio's orchestrator, not the model alone, decides when tools run.
