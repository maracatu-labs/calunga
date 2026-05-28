# Calunga

**Civic oversight of Brazilian public administration, to the beat of the people.**

Open source platform that makes Brazilian public spending accessible to any citizen via natural language chat.

[maracatu.org](https://maracatu.org) · [Contributing](CONTRIBUTING.md) · [Code of Conduct](CODE_OF_CONDUCT.md) · [Security](SECURITY.md)

## What it is

The data exists — it's public, it's open. But it's scattered across dozens of portals, in different formats, wrapped in bureaucratic language. Calunga is a conversational platform where you ask in plain Portuguese and get clear answers, with data, sources, and alerts for irregularities.

```
you ask:         "quanto o deputado X gastou em 2025?"
                 "essa empresa que recebeu o contrato é regular?"
                 "me mostra os gastos suspeitos dessa semana"

calunga responde com dados reais da Câmara, Senado, Portal da Transparência,
Receita Federal e SICONFI — tabelas, gráficos, links para fontes oficiais,
e alertas quando algo parece irregular.
```

## Components

Calunga is part of the **Maracatu** project ([maracatu.org](https://maracatu.org)). Its components are named after elements of the Pernambuco cultural manifestation that gives the initiative its name:

| Name | What it is |
|------|---------|
| **Calunga** | AI agent (LangGraph + Gemini) — the sacred doll that protects the nation |
| **Baque** | Ingestion pipeline (Dagster + Celery) — the beat that never stops |
| **Gonguê** | Anomaly classifiers — the bell that warns |
| **Terreiro** | REST API (FastAPI) — the space where everything meets |
| **Cortejo** | Web frontend (Next.js) — the public procession |

## Stack

| Layer | Technology |
|--------|-----------|
| Frontend | Next.js 15 (App Router), Tailwind v4, Vercel AI SDK, Recharts |
| API | FastAPI, Pydantic v2, asyncpg (raw SQL) |
| AI agent | LangGraph, langchain-google-genai (Gemini 2.5 Flash / Pro with fallback) |
| Database | PostgreSQL 16 + pgvector |
| Embeddings | BGE-M3 via Hugging Face (1024 dim) |
| Cache | Redis 7 |
| Pipeline | Dagster + Celery Beat |
| ML | scikit-learn (K-Means) |
| Reverse proxy | Traefik v3 (label-based routing) |
| Public ingress | Cloudflare Tunnel (no inbound ports on the host) |
| Error capture | Sentry (optional) |
| Backups | `pg_dump` → Cloudflare R2 (S3-compatible, optional) |

## Data sources

All free and open:

- **Câmara dos Deputados** — CEAP, deputies, parties, votes
- **Senado Federal** — senator CEAP, votes
- **Portal da Transparência** — sanctions (CEIS, CNEP, CEPIM), CPGF, contracts, travel, earmarks
- **Receita Federal** — CNPJ registry (CSV bulk) + BrasilAPI (on-demand)
- **SICONFI / Tesouro Nacional** — fiscal data from states and capitals
- **TSE** — candidates and campaign finance reports

## Quickstart

Requirements: Docker, Docker Compose, `make`. For local development without Docker: Python 3.12+ with [`uv`](https://docs.astral.sh/uv/) and Node.js 20+.

```bash
git clone git@github.com:maracatu-labs/calunga.git
cd calunga

cp .env.example .env
# fill GOOGLE_API_KEY (required) and TRANSPARENCIA_API_TOKEN (optional)

make dev
```

That's it. Frontend at [http://localhost:3000](http://localhost:3000), API at [http://localhost:8000](http://localhost:8000), Dagster at [http://localhost:3002](http://localhost:3002).

To seed the database with real data, open Dagster and trigger the `carga_fase1_backfill` job (the sensor cascade handles the remaining phases).

## Useful commands

| Command | What it does |
|---------|-----------|
| `make dev` | Brings everything up (database, API, frontend, Dagster) |
| `make down` | Stops the containers (preserves data) |
| `make db-migrate` | Applies SQL migrations |
| `make test` | Runs the tests |
| `make logs` | Logs from all containers |
| `make backup` | Dumps the database into `backups/` |
| `make help` | Lists all targets |

## Structure

```
calunga/
├── cortejo/         # Next.js frontend
├── terreiro/        # FastAPI backend + Calunga agent + Gonguê classifiers
│   ├── app/         # FastAPI + LangGraph + SQL queries
│   ├── pipeline/    # Dagster assets (Baque)
│   ├── migrations/  # Plain SQL (yoyo-migrations)
│   └── tests/       # pytest
├── infra/
│   ├── edge/        # Traefik + cloudflared (single public ingress)
│   └── backup/      # Postgres → R2 backup notes
├── scripts/         # Operational utilities
├── docker-compose.yml
└── Makefile
```

## Production deployment

Calunga at [maracatu.org](https://maracatu.org) runs on a self-hosted Linux host fronted by Cloudflare Tunnel — no inbound ports on the network, TLS terminated at Cloudflare.

```
                  Internet
                      │  (TLS at Cloudflare)
                      ▼
            ┌─────────────────────┐
            │  Cloudflare Tunnel  │  cloudflared (outbound only)
            └──────────┬──────────┘
                       │
                       ▼
            ┌─────────────────────┐
            │      Traefik        │  reverse-proxy (routes by labels)
            └──────────┬──────────┘
                       │
       ┌───────────────┼───────────────┐
       ▼               ▼               ▼
   ┌────────┐     ┌────────┐      ┌────────┐
   │  web   │     │  api   │      │   db   │
   │ (3000) │     │ (8000) │      │ (5432) │
   └────────┘     └────────┘      └────────┘
```

The host directory layout is:

```
/srv/
├── edge/        # Traefik + cloudflared (this stack creates the edge_proxy network)
├── calunga/     # Application stack (this repo)
└── backups/     # Local pg_dump snapshots
```

Bootstrap:

```bash
# Edge first (one-time)
cd /srv/edge
cp .env.example .env  # fill CLOUDFLARE_TUNNEL_TOKEN
docker network create edge_proxy
docker compose up -d

# Then the application
cd /srv/calunga
cp .env.example .env  # fill secrets, set APP_ENV=production, CALUNGA_HOST=...
docker compose up -d
```

In `production`, the API refuses to start with the default `JWT_SECRET`. Generate one with `openssl rand -hex 32`. See [`infra/edge/README.md`](infra/edge/README.md) for the Cloudflare side and [`infra/backup/README.md`](infra/backup/README.md) for off-site backups.

### Continuous deployment

Every push to `main` deploys automatically. No human SSH'es into the server.

```
PR opened ──► CI (.github/workflows/ci.yml)
              GitHub-hosted ubuntu-latest
              backend: uv sync + ruff + pytest
              frontend: npm ci + tsc + next build
              gate: must be green to merge
                       │
              squash merge into main
                       │
              CI runs again on main, must be green
                       │
              workflow_run triggers deploy (.github/workflows/deploy.yml)
              runs on self-hosted runner on the maracatu-lab host
                       │
              pull main │ snapshot images as :rollback
                        │ docker compose build api web
                        │ docker compose up -d api web
                        │ poll healthchecks (≤ 90s)
                        │ smoke test https://maracatu.org/health (6 attempts)
                       │
              success ──► done (~3 minutes warm cache)
              failure ──► retag :rollback to :latest, restart, alert via job status
```

Workflows:

| File | Purpose |
|------|---------|
| [`.github/workflows/ci.yml`](.github/workflows/ci.yml) | Quality gate. Runs on every PR and push. |
| [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml) | Self-hosted deploy. Triggered by `workflow_run` of CI on `main`, plus a manual `workflow_dispatch` escape hatch. |
| [`.github/workflows/guard-workflow-changes.yml`](.github/workflows/guard-workflow-changes.yml) | Blocks fork PRs that touch `.github/`. Second gate on top of repo-level "Require approval for outside collaborators". |

Operational notes:

- **No secrets in GitHub.** Real env lives only in `/srv/calunga/.env` on the host. CI runs without any `secrets.X` reference; deploy reads env from the host directly.
- **Manual deploy** when needed: go to the [`deploy` workflow](https://github.com/maracatu-labs/calunga/actions/workflows/deploy.yml) and click "Run workflow" on `main`.
- **Rollback** is automatic if `https://maracatu.org/health` fails the smoke test, by retagging the previous `calunga-api:rollback` and `calunga-web:rollback` images. To roll back a successful-but-bad deploy manually, SSH into the host and run `docker tag calunga-api:rollback calunga-api:latest && docker tag calunga-web:rollback calunga-web:latest && docker compose -f /srv/calunga/docker-compose.yml up -d api web`.
- **Branch protection on `main`** is enforced: PRs only, required status checks (`backend` + `frontend`), no force pushes, no deletions, no bypass — even for admins. `enforce_admins: true`.
- **Self-hosted runner** is a systemd service on the host: `actions.runner.maracatu-labs-calunga.maracatu-lab.service`. Runs as user `anderson`, label `maracatu-lab`, working dir `/srv/runner/`.
- **Cold-cache build** (after a `pyproject.toml` change or Dockerfile reorder) re-fetches the BGE-M3 weights (~2 GB) and takes ~15–20 min. Warm-cache deploys take ~3 min.

### Hardening summary

- All container ports bind to `127.0.0.1` (only Traefik exposes 80 inside `edge_proxy`)
- `cap_drop: [ALL]` + `no-new-privileges` on every service
- API enforces `JWT_SECRET` strength in production, daily Gemini token quotas per user, magic-link rate limits per email and per IP, message-size caps, and a hardened LLM system prompt against indirect prompt injection
- Frontend ships strict CSP, X-Frame-Options DENY, X-Content-Type-Options, Referrer-Policy and Permissions-Policy headers, plus `rehype-sanitize` on rendered chat markdown
- Optional Sentry capture (server + client) gated by DSN envs

## Contributing

Every contribution is welcome — code, documentation, bug reports, classifier suggestions, new public datasets to integrate. Read [CONTRIBUTING.md](CONTRIBUTING.md) for the PR workflow and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for what we expect from the community environment.

Found a vulnerability? See [SECURITY.md](SECURITY.md) before opening a public issue.

## License

[MIT](LICENSE).
