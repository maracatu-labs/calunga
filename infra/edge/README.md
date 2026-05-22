# Edge stack

Single public ingress for every container on the host. Lives under `/srv/edge/`
on the production server.

## Components

- **cloudflared** — Cloudflare Tunnel daemon. Holds an outbound connection to
  Cloudflare; no inbound ports are opened on the host. Cloudflare terminates
  TLS, applies WAF/rate limit rules and forwards traffic over the tunnel.
- **traefik** — Reverse-proxy that watches Docker labels and routes by
  `Host` + `PathPrefix`. Listens on `:80` inside the `edge_proxy` network.
  Dashboard on `127.0.0.1:8080` (reachable only via SSH tunnel).

```
Internet
   |  (TLS at Cloudflare)
   v
Cloudflare Tunnel  ──>  cloudflared  ──>  traefik  ──>  app containers
                                            ^                ^
                                            |                |
                                       label-based routing on edge_proxy
```

## Bootstrap

```bash
# 1. Create the shared external network (one-off)
docker network create edge_proxy

# 2. Clone this folder onto the host (typically /srv/edge/)
cp .env.example .env  # fill CLOUDFLARE_TUNNEL_TOKEN

# 3. Start the stack
docker compose up -d
```

The `edge_proxy` network is consumed by every project stack (`/srv/calunga`,
future projects). Each project attaches its public-facing service to
`edge_proxy` and declares Traefik labels; nothing else is exposed.

## Cloudflare Tunnel configuration

In the Cloudflare Zero Trust dashboard, under **Networks > Tunnels >
maracatu-lab > Public Hostnames**:

| Subdomain | Domain        | Service                |
|-----------|---------------|------------------------|
| _empty_   | maracatu.org  | `http://traefik:80`    |
| www       | maracatu.org  | `http://traefik:80`    |

Traefik handles path-based routing (`/v1` and `/health` to the API, everything
else to the web frontend) via labels declared in the project stacks.

## Operations

```bash
# Inspect logs
docker compose logs -f cloudflared
docker compose logs -f traefik

# Restart
docker compose restart

# Reach the Traefik dashboard from your laptop
ssh -L 8080:127.0.0.1:8080 maracatu-lab
# then open http://localhost:8080 in your browser
```

## Hardening notes

- `traefik` mounts `/var/run/docker.sock` read-only for service discovery.
  This is the standard self-hosted pattern but represents a privilege
  surface; a future hardening step is to put `tecnativa/docker-socket-proxy`
  in front of it.
- Memory limits cap each container at 256MiB.
- `cap_drop: [ALL]` and `security_opt: no-new-privileges` applied where
  feasible (traefik keeps default caps to read the socket).
