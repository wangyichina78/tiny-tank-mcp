<!--
Brief (for the author, delete before circulating)
Reader: the same Python developer, now asked to host an MCP server where company agents can reach it.
Hard claim: publishing an MCP server is publishing a small stateless web service. The MCP-specific parts are three settings (Host/Origin allowlist, path, no GET probe) and one rule (no deploy without green checks).
Kept thin: Render itself, which is only the worked example.
Kept off the page: company names, the author's personal Render account and URL.
-->

# MCP Publish: Hosting an MCP Server

> **Reference material only.** This is not production software. Review and vet it fully before using any part of it, and don't adopt it into a work environment as it is. Whoever uses it takes full responsibility for that use. See [DISCLAIMER.md](DISCLAIMER.md).

`MCP_Guide.md` ends with a server running on `127.0.0.1`. This document covers everything between that and a company agent calling it over HTTPS: packaging, configuration, hosting, TLS, the deploy pipeline, verification, the gateway, connecting agents, and day-two operations.

Render, a hosted container platform, is used as the worked example because the full path was actually run on it. The company platform will differ, so each step says what the equivalent usually is on an enterprise platform. Those mappings are typical patterns. Confirm what your platform actually runs with the platform owners.

## 1. What "published" means

A published MCP server is a container running somewhere that the AI client can reach over HTTPS, at one path (`/mcp`). Nothing about it is AI-specific. If your team can host a small stateless REST API, it can host this.

```
 AI client ──HTTPS──► [MCP gateway] ──► ingress / TLS ──► container :PORT ──► your data
 (Copilot Studio,      optional:          terminates TLS,    the MCP server      DB or API
  Claude, ...)         auth, tool          WAF, rate limit    (stateless,         (read-only
                       allowlist, logs                         JSON responses)     account)
```

**Reachability is the first thing to settle.** Copilot Studio runs in Microsoft's cloud, so the endpoint must be reachable from there. Usually that means an internet-facing HTTPS endpoint protected by the gateway and network rules, unless your Power Platform team has a private connectivity option for MCP. Ask them before choosing a host. It decides the whole layout. A server reachable only on the internal network will work for agents running internally, such as Claude Code on a developer laptop on the VPN, and will fail for cloud agents.

## 2. Before you start

| Item | Who usually provides it | Why it blocks |
|---|---|---|
| Security approval for the endpoint, including its auth model | Cyber security | Nothing goes live without it. See `MCP_Security.md` |
| A host, container registry and ingress with TLS | Cloud or platform team | Where the container runs |
| An MCP gateway route, if the company has one | Gateway or API team | Auth, tool allowlist, logging |
| Agent platform policy allowing MCP connectors | Power Platform admins (for Copilot Studio) | Data policies often block new connector types by default |
| Network allowlist entries for testers and agent platforms | Network team | Testers and agents can't reach the endpoint without them |
| Write access to the source repo for any automation that pushes | Repo admins | Automation that can't push stalls the pipeline |

The last two each cost time during the dry run. The repo automation was refused with HTTP 403 until its app was granted write access to the repository, and the test machine's outbound proxy blocked the hosting domain until it was allowlisted. Raise both on day one.

## 3. Package it as a container

The `Dockerfile` in this package:

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/

# Port: MCP_PORT, else the platform's PORT, else 8000.
ENV MCP_HOST=0.0.0.0 \
    PYTHONUNBUFFERED=1

RUN useradd --no-create-home --uid 10001 app
USER app

EXPOSE 8000
CMD ["python", "-m", "src.server"]
```

Line by line:

- **`python:3.12-slim`**: pin the minor version and keep it the same as CI. Tool descriptions published from docstrings differ between Python 3.12 and 3.13, which changes what agents see. The server now uses explicit description strings, and CI runs both versions to catch it, but runtime and CI should still match. Enterprise builds should pin the image by digest and pull it from the company registry.
- **Dependencies are installed before the code is copied**, so code changes don't reinstall packages. `requirements.txt` pins `mcp>=2.3,<3.0` so a major SDK release can't arrive unannounced.
- **Only `src/` goes into the image.** Tests, docs and tools stay out. One gap remains: `requirements.txt` also lists `pytest`, so the test runner is installed in the image. For production, split runtime and development requirements so the image carries only the runtime ones.
- **`MCP_HOST=0.0.0.0`**: inside a container the server must listen on all interfaces, or the platform's router can't reach it. Locally the default stays `127.0.0.1`.
- **The port** comes from `MCP_PORT`, else from `PORT` (which Render, Cloud Run and Heroku set), else 8000.
- **`USER app`**: the server never runs as root.

Build and test the image locally before any host is involved:

```bash
docker build -t tiny-tank-mcp:local .
docker run --rm -p 8000:8000 -e MCP_ALLOWED_HOSTS="127.0.0.1:*" tiny-tank-mcp:local
python tools/smoke_test.py --url http://127.0.0.1:8000/mcp          # expect ALL PASS
```

## 4. Configure it

All configuration is environment variables. There are no config files and no secrets in the image.

| Variable | Set to | Notes |
|---|---|---|
| `MCP_HOST` | `0.0.0.0` in containers | Set by the Dockerfile |
| `MCP_PORT` / `PORT` | Whatever the platform routes to | Most platforms set `PORT` themselves |
| `MCP_ALLOWED_HOSTS` | The public hostname, e.g. `tiny-tank-mcp.example.com` | Requests with any other `Host` header get HTTP 421. This is the DNS-rebinding defence |
| `MCP_ALLOWED_ORIGINS` | `https://` plus your hostname, plus each browser-based client's origin | Requests with any other `Origin` get HTTP 403 |

**`MCP_ALLOWED_HOSTS` is mandatory when the server listens on anything other than loopback.** On `127.0.0.1` the SDK restricts Host headers to localhost by itself. On `0.0.0.0` it applies no Host check at all unless you set the list.

**Origins are where clients trip.** Clients that run in a browser send an `Origin` header with their own domain. claude.ai sends `https://claude.ai`. A parallel test session (the agent-eval branch of the repository) found that adding the server as a claude.ai connector failed with only a generic error until that origin was added. Copilot Studio may send its own origin: watch the server logs for `403` on `POST /mcp` while connecting it, and add exactly the origin it sends. **Never set `*`.** That switches the defence off.

If a gateway sits in front and rewrites the `Host` header, add the gateway's upstream hostname as well.

## 5. Host it: the Render walk-through

Render builds the `Dockerfile` straight from the GitHub repository. The file `render.yaml` describes the service:

```yaml
services:
  - type: web
    name: tiny-tank-mcp
    runtime: docker
    plan: free
    autoDeploy: true
    envVars:
      - key: MCP_ALLOWED_HOSTS
        sync: false
      - key: MCP_ALLOWED_ORIGINS
        sync: false
```

`sync: false` makes Render ask for those two values at setup, so they can't be skipped by accident.

The steps that were run:

1. **Sign in to Render with GitHub,** and grant it access to this one repository only.
2. **Choose New, then Blueprint,** and select the repository. Render reads `render.yaml`.
3. **Enter the two allowlist values** when prompted, using the hostname Render assigns (`<service>.onrender.com`).
4. **Wait for the first deploy.** Render clones the repo, builds the Dockerfile, starts the container and routes HTTPS traffic to it. The log shows `Uvicorn running on http://0.0.0.0:10000` when it's ready. Render's `PORT` is 10000, and the server picked it up without changes.
5. **Verify from outside** (section 8).

What Render did that an enterprise platform does differently:

| Render did this | Typical enterprise equivalent (confirm with your platform team) |
|---|---|
| Built the image from the repo on every push | CI builds the image, scans it, and pushes it to the company registry, tagged with the commit SHA |
| Managed HTTPS and the certificate automatically | Ingress controller or load balancer with a company certificate |
| Put Cloudflare in front, including a WAF | The company WAF or edge service |
| Stored env vars in its dashboard | Platform config, plus a secret store (such as Key Vault) for anything sensitive |
| Deployed on every push to `main` | Deploy after CI passes, with an approval step for production |
| Slept the free service when idle | Keep at least one instance always running |
| Logs in its dashboard | Central logging (the server writes JSON lines to stderr) |

For a Microsoft-centred company the usual candidates are Azure Container Apps, App Service for Containers or AKS, with Azure API Management as the gateway. That's an inference from the agent platform being Copilot Studio. Nobody involved in this package has seen your environment.

## 6. Ingress and TLS settings

- **Terminate TLS at the ingress** and forward plain HTTP to the container port. Agents connect over HTTPS only.
- **Don't buffer responses.** Replies are JSON in this configuration, but clients may still negotiate an event stream.
- **Health probe: use a TCP check on the port, never `GET /mcp`.** A GET on the MCP path opens a long-lived event stream, so an HTTP probe hangs and the platform restarts a healthy container. There is no separate `/health` route. If your platform insists on HTTP probes, add one.
- **Limit request body size.** The SDK rejects bodies over its limit (a 5 MB test body was refused), and the ingress should cap well below that too.
- **Rate limit** at the ingress or gateway. Any internet-facing endpoint gets scanned within days.
- **Expect the WAF to block some attack strings** before they reach the server. On Render, Cloudflare returned HTTP 403 for `TK-102; DROP TABLE tanks` and `../../etc/passwd`. That's useful defence in depth, but it means the direct route and the gateway route won't return identical answers for attack inputs. Plan for that in the parity test (section 9).

## 7. The deploy pipeline: no deploy without green checks

`.github/workflows/ci.yml` runs on every push and pull request, on Python 3.12 and 3.13:

1. Install the requirements.
2. Run all tests: functional, protocol and security (79 tests).
3. Start the server and run the live smoke test and the black-box security check against it.

**The gap found in the dry run:** Render's auto-deploy and CI both start on the same push and run independently, so a commit that fails CI is deployed anyway. On an enterprise pipeline, make the deploy a later stage of the same pipeline:

```
push → CI (tests + live checks) → build image, tag with SHA → deploy to test → smoke + security check
     → approval → deploy to production → smoke + security check
```

Rules worth enforcing in the pipeline itself, where they can't be skipped:

- **No deploy unless CI on that exact commit is green.**
- **Images are tagged with the commit SHA, never `latest`,** so every piece of evidence points to one build.
- **Production needs a person's approval.**
- **A changed tool definition stops the pipeline.** The security test SEC-01 compares the live tool definitions with a pinned hash, and a reviewer must approve the new hash before it ships. See `MCP_Security.md`.

## 8. Verify every deployment

Run both checks from outside the platform, against the real URL, after every deploy:

```bash
python tools/smoke_test.py --url https://<host>/mcp --timeout 90 --out evidence/smoke-<date>.json
python -m tools.security_check --url https://<host>/mcp --timeout 90 --out evidence/security-<date>.json
```

The smoke test checks the handshake, the tool list, and 16 calls with known answers. The security check runs SEC-01 to SEC-05 as an outsider would. Both write JSON evidence files. Keep them, because they are what the security team will ask for.

`--timeout 90` covers a cold start. Exit code 0 means all checks passed, 1 means a check failed, and 2 means the endpoint couldn't be reached properly. A 2 points to a network, TLS, path or allowlist problem, and the server's logic may be fine.

The security check should be run by **someone other than the developer**, from their own network. That is the "independent" in the independent test cadence, and it also proves the endpoint is reachable from where it needs to be.

## 9. Put the gateway in front

A gateway is where the company enforces things the server shouldn't decide for itself:

- **Authentication:** who may call at all. This POC has none. Anything with real data needs it, ideally passing the signed-in user's identity through so the server can apply per-user permissions.
- **A tool allowlist by name:** the gateway forwards only `tools/call` for approved tool names. This is the main control for third-party MCP servers whose code you don't own.
- **Logging and a request ID,** so a gateway log line can be matched to the server's `call_id`.
- **Rate limiting and quotas.**

After the route exists, prove it changes nothing that matters:

```bash
export MCP_GATEWAY_AUTH_HEADER="<header name>"     # from the gateway team
export MCP_GATEWAY_AUTH_VALUE="<value>"            # from the vault; never committed, never printed
python tools/smoke_test.py --url https://<gateway>/<route>/mcp --out evidence/gateway.json
python tools/compare_routes.py evidence/smoke-<date>.json evidence/gateway.json
```

`compare_routes.py` compares every field of every call. Expect `Parity PASS`. If the gateway has a WAF, agree in advance with security that "blocked at the edge" is an accepted difference for attack inputs, before the first comparison fails on it.

## 10. Connect the agents

**Claude Code** (a developer tool, useful for testing):

```bash
claude mcp add --transport http tiny-tank https://<host>/mcp
```

**claude.ai:** in Settings, under Connectors, add a custom connector with the URL. The server's `MCP_ALLOWED_ORIGINS` must include `https://claude.ai`.

**Copilot Studio:** in the agent, add a tool of type Model Context Protocol, then give it the server URL and the authentication the gateway requires. Menu names change between releases, so follow Microsoft's current documentation for the exact path. Then:

1. Check that the tools appear in the agent's tool list. Switch off any the agent doesn't need.
2. Put the operating rules in the agent's instructions: answer only from tool results, cite the tool for each fact, ask again on `INVALID_INPUT`. Don't rely on the server's `instructions` field reaching the model, because clients differ.
3. Ask the test questions from the README ("Which tanks at Site B need attention, and why?"), and check the answers against the known planted cases.

## 11. Operate it

- **Logs:** one JSON line per tool call on stderr (timestamp, tool, call ID, validated subject, result code, duration). No headers, tokens or raw arguments. Ship them to central logging.
- **Scaling:** stateless, so add instances behind the load balancer. No sticky sessions are needed.
- **SDK upgrades:** within `<3.0`, run the full CI. If SEC-01 fails because the SDK changed how it publishes definitions, review the difference before re-pinning. A major-version upgrade is a project of its own.
- **Rollback:** redeploy the previous commit's image by its SHA tag, then rerun the smoke test and the security check.
- **Teardown:** an endpoint without authentication must have an end date. Delete the service, the route and the DNS entry when testing ends.

## 12. What the dry run actually hit

Every item below happened while publishing this package. Each one will exist in some form on a company platform.

| What happened | How long it blocked | Do this up front |
|---|---|---|
| Automation could read the repo but not push to it (HTTP 403) | Several rounds | Grant the repo app write access before work starts |
| The test machine's outbound proxy blocked the hosting domain | One round | Get tester and agent network allowlist entries raised early |
| CI failed on Python 3.12 only: the tool description came out different from 3.13 | One fix | Use explicit description strings, and run CI on the runtime version |
| Render deployed while CI was still running | No harm this time | Make deploy a pipeline stage after CI |
| The WAF blocked attack strings, and the security check first mistook this for an outage | One fix | Treat a 4xx on attack input as refused upstream |
| claude.ai couldn't add the connector because its Origin wasn't allowlisted (found in the parallel agent-eval session) | One fix | List each client's origin when configuring |
| The free host slept, so the first call took up to a minute | Recurring | Always-on instances in any real environment |
