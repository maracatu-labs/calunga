# Contribuindo com o Calunga

Obrigado pelo interesse em contribuir! Calunga é um projeto open source que existe para ampliar o acesso de qualquer cidadão aos gastos públicos brasileiros. Toda forma de ajuda conta — código, documentação, sugestão de classificadores, novas fontes de dados, relato de bug.

## Antes de começar

- Leia o [Código de Conduta](CODE_OF_CONDUCT.md).
- Encontrou uma vulnerabilidade? Não abra issue pública. Siga o [SECURITY.md](SECURITY.md).
- Para mudanças grandes (refatorações, novas features), abra uma issue antes para discutir a abordagem.

## Como rodar o projeto

Pré-requisitos: Docker, Docker Compose e `make`. Para desenvolvimento sem Docker, também Python 3.12+ com [`uv`](https://docs.astral.sh/uv/) e Node.js 20+.

```bash
git clone git@github.com:maracatu-labs/calunga.git
cd calunga
cp .env.example .env

make dev
```

`GOOGLE_API_KEY` é obrigatória para o chat funcionar. `TRANSPARENCIA_API_TOKEN` é opcional, mas necessária para as fontes do Portal da Transparência.

## Fluxo de PR

1. Faça fork do repositório.
2. Crie um branch a partir de `main` com nome descritivo (`feat/...`, `fix/...`, `docs/...`).
3. Faça seus commits seguindo a [convenção abaixo](#mensagens-de-commit).
4. Rode `make test` localmente antes de abrir o PR.
5. Abra o PR descrevendo o problema, a solução e como testar.
6. Aguarde revisão. Toda contribuição passa por code review.

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

## Convenções de código

### Python (`terreiro/`)

- Use `uv` para gerenciar dependências (`uv add`, `uv sync`). Não use `pip` ou `poetry`.
- SQL nativo com `asyncpg`, sempre parametrizado (`$1`, `$2`). Sem ORM.
- Schemas Pydantic v2 são a fonte única de verdade entre API e tools do agente.
- Async em todo lugar (httpx, asyncpg, FastAPI).
- Migrations em SQL puro com `yoyo-migrations` em `terreiro/migrations/`.
- Sem comentários no código além de docstrings — nomes claros valem mais.

### TypeScript (`cortejo/`)

- App Router do Next.js 15 (não Pages Router).
- Server Actions em `src/lib/actions.ts` — sem `useEffect` para dados, sem `fetch` no cliente.
- `useChat()` do Vercel AI SDK para consumir SSE.
- Gráficos via Recharts com formatação BRL.
- Sem comentários inline além de JSDoc — nomes claros valem mais.

### Geral

- Código em inglês (variáveis, funções, classes).
- Conteúdo voltado ao usuário em português brasileiro.
- Valores monetários sempre em `DECIMAL(12,2)` no banco e na API.

## Adicionando uma nova fonte de dados

1. Adicione o cliente HTTP em `terreiro/app/services/`.
2. Adicione um asset do Dagster em `terreiro/pipeline/definitions.py` (com `RetryPolicy` se chamar API externa).
3. Adicione a migration SQL em `terreiro/migrations/`.
4. Adicione queries em `terreiro/app/queries/`.
5. Crie a tool da Calunga em `terreiro/app/agent/tools.py` seguindo o contrato unificado (`modo` + `fonte`).
6. Cubra com testes em `terreiro/tests/`.

## Reportando bugs

Use o template de issue. Inclua:
- Versão do Docker / Python / Node
- Passos para reproduzir
- O que esperava vs. o que aconteceu
- Logs relevantes (`make logs-api`, `make logs-web`)

## Dúvidas

Abra uma issue marcando como `question` ou inicie uma discussion no GitHub.
