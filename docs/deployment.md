# Deployment Guide: Public HTTPS Host

## Before you deploy

| # | Item | Why |
|---|---|---|
| 1 | Accept that the endpoint has no authentication: anyone who knows the URL can call it | Acceptable only because the data is synthetic and the tool is read-only |
| 2 | A host that terminates TLS and forwards to the container port (`MCP_PORT`, else `PORT`, else 8000) | Agents connect over HTTPS only |
| 3 | If an organization's agent will call it, that organization's security reviewer approves calling an external no-auth MCP endpoint, and its agent platform's data policy allows MCP connectors | Their policy, not yours, decides whether their agent may connect |
| 4 | If routed through an MCP gateway: the route, header pass-through rules, and request-ID header name | Needed for the gateway parity check |

## Quick option: Render (free)

1. Sign up at https://render.com with **Sign in with GitHub**. Grant access to the `tiny-tank-mcp` repository only.
2. In Render, choose **New**, then **Blueprint**, and pick the repo. Render reads `render.yaml` (free plan, Docker build).
3. When it asks for the two variables, enter the service hostname. If the name `tiny-tank-mcp` is taken, Render adds a suffix, so check the URL it shows.
   - `MCP_ALLOWED_HOSTS` = `tiny-tank-mcp.onrender.com`
   - `MCP_ALLOWED_ORIGINS` = `https://tiny-tank-mcp.onrender.com`

   Some agent clients send an `Origin` header with their own domain. Any origin not on this list gets HTTP 403, and the client typically reports only that the connector could not be added. Add each client's origin, comma-separated. For example, claude.ai needs `https://claude.ai`. For Copilot Studio, check its requests in the Render logs (a 403 on `POST /mcp`) and add the origin it sends. Do not use `*`: the Origin check is the DNS-rebinding defence (SEC-04).
4. Wait for the first deploy. This is also the first real build of the Dockerfile.
5. Verify from your machine:
   ```bash
   python tools/smoke_test.py --url https://tiny-tank-mcp.onrender.com/mcp --out evidence/direct.json
   python -m tools.security_check --url https://tiny-tank-mcp.onrender.com/mcp --out evidence/security.json
   ```

The free plan sleeps after a period with no traffic. The first call after that can take up to a minute, and an agent may time out. Call it once with the smoke test to wake it, then use the agent. When testing ends, delete the service in Render (**Settings**, then **Delete Web Service**).

The sections below are for a container host you run yourself.

## 1. Build and push

```bash
docker build -t <registry>/tiny-tank-mcp:<git-sha> .
docker push <registry>/tiny-tank-mcp:<git-sha>
```

Tag images with the commit SHA. Do not use `latest`, so the gateway parity run (GT-05) is tied to a known build.

## 2. Run

The container listens on `0.0.0.0:8000` and serves `/mcp`. Set the allowlist to the public host name:

```bash
docker run -d -p 8000:8000 \
  -e MCP_ALLOWED_HOSTS="tinytank.example.com,tinytank.example.com:*" \
  -e MCP_ALLOWED_ORIGINS="https://tinytank.example.com" \
  <registry>/tiny-tank-mcp:<git-sha>
```

If the allowlist is set, a request with a Host header that is not on it gets HTTP 421. If the gateway rewrites the Host header, add the gateway's upstream host name to the list too.

## 3. Ingress

- Terminate TLS at the host or ingress and forward to container port 8000.
- A public endpoint will be found and scanned within days. Turn on the host's rate limiting if it has one. If you know your callers' egress IP ranges, restrict to them.
- Do not buffer responses. The endpoint uses JSON mode, but MCP clients may still send `Accept: text/event-stream`.
- Health probe: the image has no separate health route. Use a TCP probe on 8000. Do not probe with `GET /mcp`: it can hold open a long-lived event stream, so the probe times out instead of returning a status.

## 4. Verify direct route

```bash
python tools/smoke_test.py --url https://tinytank.example.com/mcp --out evidence/direct.json
```

Expected result: `ALL PASS`, exit code 0. Exit code 2 means a transport or HTTP problem (DNS, TLS, 404 on the path, 421 on the host).

## 5. Verify gateway route (GT-01, GT-03, GT-05)

```bash
export MCP_GATEWAY_AUTH_HEADER="<header name>"
export MCP_GATEWAY_AUTH_VALUE="<value>"        # from the vault, never committed
python tools/smoke_test.py --url https://<gateway>/<route>/mcp --out evidence/gateway.json
python tools/compare_routes.py evidence/direct.json evidence/gateway.json
```

Expected result: `Parity PASS`.

## 6. Connect an agent

**Claude Code:**

```bash
claude mcp add --transport http tiny-tank https://tinytank.example.com/mcp
```

**Copilot Studio:** add an MCP tool in the agent with the Streamable HTTP transport and the direct URL, with no authentication. Then:

1. Check that `get_tank_status` appears in the agent's tool list (IT-01).
2. Ask "What is the status of tank TK-102?" The expected answer is Inspection Due, Site A, with the synthetic source cited.
3. Ask about TK-999 (expect not found) and TANK-102 (expect the agent to ask for a valid ID).
4. If you use a gateway, repeat the steps through the gateway URL.

## 7. Teardown

Take the endpoint down when testing ends. It has no authentication, so do not leave it running unattended.
