<div align="center">

# Calunga

**Civic oversight of Brazilian public administration, to the beat of the people.**

Open source platform that makes Brazilian public spending accessible to any citizen via natural language chat.

[maracatu.org](https://maracatu.org) · [Contributing](CONTRIBUTING.md) · [Code of Conduct](CODE_OF_CONDUCT.md) · [Security](SECURITY.md)

</div>

---

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
| Infra | Docker Compose, Caddy (auto-SSL) |

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
# preencha GOOGLE_API_KEY (obrigatório) e TRANSPARENCIA_API_TOKEN (opcional)

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
├── scripts/         # Operational utilities
├── docker-compose.yml
├── Makefile
└── Caddyfile
```

## Contributing

Every contribution is welcome — code, documentation, bug reports, classifier suggestions, new public datasets to integrate. Read [CONTRIBUTING.md](CONTRIBUTING.md) for the PR workflow and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for what we expect from the community environment.

Found a vulnerability? See [SECURITY.md](SECURITY.md) before opening a public issue.

## License

[MIT](LICENSE).
