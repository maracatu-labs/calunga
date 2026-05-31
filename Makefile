.PHONY: help setup dev up down restart logs db-migrate db-migrate-mark api web health test-api test-chat clean

help: ## Mostrar comandos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Setup inicial: copiar .env e instalar deps
	@test -f .env || cp .env.example .env && echo ".env criado"
	cd terreiro && uv sync
	cd cortejo && npm install

dev: ## Setup + subir containers + migrate + seed (pronto para usar)
	@if [ ! -f .env ]; then cp .env.example .env && echo ".env criado — preencha GOOGLE_API_KEY"; \
	else while IFS='=' read -r key val; do \
	    case "$$key" in \#*|"") continue;; esac; \
	    grep -q "^$$key=" .env 2>/dev/null || echo "$$key=$$val" >> .env; \
	done < .env.example; fi
	docker compose up -d --build
	@echo "Aguardando banco ficar pronto..."
	@until docker compose exec db pg_isready -U maracatu -q 2>/dev/null; do sleep 1; done
	@echo ""
	@echo "✔ Calunga rodando!"
	@echo "  Frontend:  http://localhost:3000"
	@echo "  LLM:       Gemini 2.5 Flash/Pro (Google)"
	@echo ""
	@echo "Primeiro uso? Rode: make db-migrate"
	@echo "  O Dagster cuida da ingestão de dados automaticamente."

up: ## Subir todos os containers
	docker compose up -d

up-build: ## Subir com rebuild das imagens
	docker compose up -d --build

down: ## Derrubar todos os containers
	docker compose down

restart: ## Reiniciar api e web
	docker compose restart api web

logs: ## Ver logs de todos os containers
	docker compose logs -f

logs-api: ## Ver logs só da API
	docker compose logs -f api

logs-web: ## Ver logs só do frontend
	docker compose logs -f web

db-migrate: ## Rodar migrations pendentes (yoyo apply)
	docker compose exec -T api python /scripts/migrate.py

db-migrate-mark: ## Marcar migrations legadas como aplicadas sem rodar SQL (yoyo mark, uso unico)
	docker compose exec -T api python /scripts/migrate.py --mark-only

db-shell: ## Abrir psql no container
	docker compose exec db psql -U maracatu -d maracatu

db-reset: ## Dropar e recriar tabelas
	docker compose exec -T db psql -U maracatu -d maracatu < terreiro/migrations/0001.create-tables.rollback.sql
	$(MAKE) db-migrate

dev-api: ## Rodar API localmente (sem Docker)
	cd terreiro && uv run uvicorn app.main:app --reload --port 8000

dev-web: ## Rodar frontend localmente (sem Docker)
	cd cortejo && npm run dev

test: ## Rodar testes unitários
	docker compose exec api python -m pytest tests/ -v

health: ## Testar endpoint de health
	@curl -s http://localhost:8000/health | python3 -m json.tool

test-api: ## Testar endpoints da API
	@echo "=== Health ==="
	@curl -s http://localhost:8000/health | python3 -m json.tool
	@echo "\n=== Deputados (primeiros 3) ==="
	@curl -s 'http://localhost:8000/v1/deputados?limit=3' | python3 -m json.tool
	@echo "\n=== Deputados SP ==="
	@curl -s 'http://localhost:8000/v1/deputados?uf=SP&limit=3' | python3 -m json.tool

test-chat: ## Testar chat via curl (SSE stream)
	@curl -N -X POST http://localhost:8000/v1/chats \
		-H "Content-Type: application/json" \
		-d '{"messages":[{"role":"user","content":"Quanto o deputado Nikolas Ferreira gastou em 2025?"}]}'

backup: ## Backup do banco de dados (PostgreSQL dump)
	@mkdir -p backups
	docker compose exec -T db pg_dump -U maracatu -d maracatu > backups/maracatu_$$(date +%Y%m%d_%H%M%S).sql
	@echo "Backup salvo em backups/"
	@ls -lh backups/*.sql | tail -1

restore: ## Restaurar backup (ex: make restore FILE=backups/maracatu_20260331.sql)
	docker compose exec -T db psql -U maracatu -d maracatu < $(FILE)

clean: ## Parar containers e limpar imagens (preserva dados do banco)
	docker compose down
	rm -rf cortejo/node_modules cortejo/.next terreiro/.venv

clean-all: ## Remover TUDO incluindo dados do banco (cuidado!)
	@echo "⚠  Isso vai apagar todos os dados (parlamentares, despesas, empresas, conversas)!"
	@echo "   Rode 'make backup' antes se quiser preservar."
	@read -p "   Tem certeza? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	docker compose down -v
	rm -rf cortejo/node_modules cortejo/.next terreiro/.venv
