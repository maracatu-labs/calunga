# Contributing to Calunga

Thanks for your interest in contributing! Calunga is an open source project that exists to broaden any citizen's access to Brazilian public spending. Every form of help counts — code, documentation, classifier suggestions, new data sources, bug reports.

## Before you start

- Read the [Code of Conduct](CODE_OF_CONDUCT.md).
- Found a vulnerability? Don't open a public issue. Follow [SECURITY.md](SECURITY.md).
- For large changes (refactors, new features), open an issue first to discuss the approach.

## How to run the project

Requirements: Docker, Docker Compose, and `make`. For development without Docker, also Python 3.12+ with [`uv`](https://docs.astral.sh/uv/) and Node.js 20+.

```bash
git clone git@github.com:maracatu-labs/calunga.git
cd calunga
cp .env.example .env

make dev
```

`GOOGLE_API_KEY` is required for the chat to work. `TRANSPARENCIA_API_TOKEN` is optional but needed for Portal da Transparência sources.

## PR workflow

1. Fork the repository.
2. Create a branch from `main` with a descriptive name (`feat/...`, `fix/...`, `docs/...`).
3. Make your commits following the [convention below](#commit-messages).
4. Run `make test` locally before opening the PR.
5. Open the PR describing the problem, the solution, and how to test it.
6. Wait for review. Every contribution goes through code review.

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/) **in English**:

```
feat(calunga): add tool to query nominal votations
fix(terreiro): scope response cache by conversation id
docs: link Dagster UI in quickstart
refactor(baque): consolidate backfill assets
test(gongue): cover electoral expense classifier
chore: bump uv dependencies
```

Accepted types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`, `style`.
Common scopes: `calunga`, `baque`, `gongue`, `terreiro`, `cortejo`.

We use **squash merge** — your PR title and description will end up as the single commit on `main`, so write both in English too.

**Don't include automatic `Co-Authored-By:` trailers** (from AI tools, for example). Add co-authorship only when another person actually collaborated on the commit.

Code identifiers (variables, functions, classes) are in English. User-facing content (UI text, error messages, this CONTRIBUTING, the README) stays in Brazilian Portuguese.

## Code conventions

### Python (`terreiro/`)

- Use `uv` to manage dependencies (`uv add`, `uv sync`). Don't use `pip` or `poetry`.
- Raw SQL with `asyncpg`, always parameterized (`$1`, `$2`). No ORM.
- Pydantic v2 schemas are the single source of truth between the API and the agent tools.
- Async everywhere (httpx, asyncpg, FastAPI).
- Migrations as raw SQL with `yoyo-migrations` in `terreiro/migrations/`.
- No inline comments beyond docstrings — clear names are worth more.

### TypeScript (`cortejo/`)

- Next.js 15 App Router (not Pages Router).
- Server Actions in `src/lib/actions.ts` — no `useEffect` for data, no client-side `fetch`.
- `useChat()` from the Vercel AI SDK to consume SSE.
- Charts via Recharts with BRL formatting.
- No inline comments beyond JSDoc — clear names are worth more.

### General

- Code identifiers (variables, functions, classes) in English.
- OSS documentation (README, this guide, code of conduct, security policy, issue/PR templates) in English.
- Strings shown to the end user inside the running app — Cortejo's UI labels, Calunga's chat responses to users — stay in Brazilian Portuguese. The audience for the deployed product is Brazilian.
- Monetary values always as `DECIMAL(12,2)` in the database and in the API.

## Adding a new data source

1. Add the HTTP client in `terreiro/app/services/`.
2. Add a Dagster asset in `terreiro/pipeline/definitions.py` (with `RetryPolicy` if it calls an external API).
3. Add the SQL migration in `terreiro/migrations/`.
4. Add queries in `terreiro/app/queries/`.
5. Create the Calunga tool in `terreiro/app/agent/tools.py` following the unified contract (`modo` + `fonte`).
6. Cover it with tests in `terreiro/tests/`.

## Reporting bugs

Use the issue template. Include:
- Docker / Python / Node version
- Steps to reproduce
- What you expected vs. what happened
- Relevant logs (`make logs-api`, `make logs-web`)

## Questions

Open an issue tagged as `question` or start a discussion on GitHub.
