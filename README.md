<div align="center">

# Calunga

**Controle social da administração pública brasileira, no ritmo do povo.**

Plataforma open source que torna os gastos públicos brasileiros acessíveis a qualquer cidadão via chat em linguagem natural.

[maracatu.org](https://maracatu.org) · [Contribuindo](CONTRIBUTING.md) · [Código de Conduta](CODE_OF_CONDUCT.md) · [Segurança](SECURITY.md)

</div>

---

## O que é

Os dados existem — são públicos, são abertos. Mas estão espalhados em dezenas de portais, em formatos diferentes, com linguagem burocrática. Calunga é uma plataforma conversacional onde você pergunta em português e recebe respostas claras, com dados, fontes e alertas de irregularidades.

```
você pergunta:   "quanto o deputado X gastou em 2025?"
                 "essa empresa que recebeu o contrato é regular?"
                 "me mostra os gastos suspeitos dessa semana"

calunga responde com dados reais da Câmara, Senado, Portal da Transparência,
Receita Federal e SICONFI — tabelas, gráficos, links para fontes oficiais,
e alertas quando algo parece irregular.
```

## Componentes

Calunga faz parte do projeto **Maracatu** ([maracatu.org](https://maracatu.org)). Os componentes carregam nomes da manifestação cultural pernambucana que dá nome à iniciativa:

| Nome | O que é |
|------|---------|
| **Calunga** | Agente de IA (LangGraph + Gemini) — boneca sagrada que protege a nação |
| **Baque** | Pipeline de ingestão (Dagster + Celery) — a batida que nunca para |
| **Gonguê** | Classificadores de anomalias — sino que alerta |
| **Terreiro** | API REST (FastAPI) — espaço onde tudo se encontra |
| **Cortejo** | Frontend web (Next.js) — a procissão pública |

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Frontend | Next.js 15 (App Router), Tailwind v4, Vercel AI SDK, Recharts |
| API | FastAPI, Pydantic v2, asyncpg (SQL nativo) |
| Agente IA | LangGraph, langchain-google-genai (Gemini 2.5 Flash / Pro com fallback) |
| Banco | PostgreSQL 16 + pgvector |
| Embeddings | BGE-M3 via Hugging Face (1024 dim) |
| Cache | Redis 7 |
| Pipeline | Dagster + Celery Beat |
| ML | scikit-learn (K-Means) |
| Infra | Docker Compose, Caddy (auto-SSL) |

## Fontes de dados

Todas gratuitas e abertas:

- **Câmara dos Deputados** — CEAP, deputados, partidos, votações
- **Senado Federal** — CEAP senadores, votações
- **Portal da Transparência** — sanções (CEIS, CNEP, CEPIM), CPGF, contratos, viagens, emendas
- **Receita Federal** — cadastro CNPJ (CSV bulk) + BrasilAPI (on-demand)
- **SICONFI / Tesouro Nacional** — dados fiscais de estados e capitais
- **TSE** — candidatos e prestação de contas

## Quickstart

Pré-requisitos: Docker, Docker Compose, `make`. Para desenvolvimento local sem Docker: Python 3.12+ com [`uv`](https://docs.astral.sh/uv/) e Node.js 20+.

```bash
git clone git@github.com:maracatu-labs/calunga.git
cd calunga

cp .env.example .env
# preencha GOOGLE_API_KEY (obrigatório) e TRANSPARENCIA_API_TOKEN (opcional)

make dev
```

Pronto. Frontend em [http://localhost:3000](http://localhost:3000), API em [http://localhost:8000](http://localhost:8000), Dagster em [http://localhost:3002](http://localhost:3002).

Para popular o banco com dados reais, abra o Dagster e dispare o job `carga_fase1_backfill` (a cascata de sensores cuida das demais fases).

## Comandos úteis

| Comando | O que faz |
|---------|-----------|
| `make dev` | Sobe tudo (banco, API, frontend, Dagster) |
| `make down` | Para os containers (preserva dados) |
| `make db-migrate` | Aplica migrations SQL |
| `make test` | Roda os testes |
| `make logs` | Logs de todos os containers |
| `make backup` | Dump do banco em `backups/` |
| `make help` | Lista todos os targets |

## Estrutura

```
calunga/
├── cortejo/         # Frontend Next.js
├── terreiro/        # API FastAPI + agente Calunga + classificadores Gonguê
│   ├── app/         # FastAPI + LangGraph + queries SQL
│   ├── pipeline/    # Assets Dagster (Baque)
│   ├── migrations/  # SQL puro (yoyo-migrations)
│   └── tests/       # pytest
├── scripts/         # Utilitários de operação
├── docker-compose.yml
├── Makefile
└── Caddyfile
```

## Contribuindo

Toda contribuição é bem-vinda — código, documentação, relatos de bug, sugestão de classificadores, dados públicos novos para integrar. Leia [CONTRIBUTING.md](CONTRIBUTING.md) para o fluxo de PRs e [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) para o que esperamos do ambiente da comunidade.

Encontrou uma vulnerabilidade? Veja [SECURITY.md](SECURITY.md) antes de abrir uma issue pública.

## Licença

[MIT](LICENSE).
