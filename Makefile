# Common tasks. Run `make help` for the list. Details: docs/DEVELOPMENT.md#commands

BACKEND  := backend
FRONTEND := frontend
UVICORN  := uv run uvicorn app.main:app --reload --port 8000

.PHONY: help setup dev demo record backend frontend test lint fmt types reset-db

help: ## Show this help
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "} {printf "  %-10s %s\n", $$1, $$2}'

setup: ## Install backend and frontend, create .env
	cd $(BACKEND) && uv sync
	cd $(FRONTEND) && npm install
	@test -f .env || (cp .env.example .env && echo "Created .env from .env.example")

dev: ## Run backend (:8000) and frontend (:5173) with modes from .env
	@trap 'kill 0' INT TERM; \
	(cd $(BACKEND) && $(UVICORN)) & \
	(cd $(FRONTEND) && npm run dev) & \
	wait

demo: ## Run both in replay mode: no keys, no searches spent
	SERPAPI_MODE=replay LLM_MODE=replay $(MAKE) dev

record: ## Run the backend in record mode (spends searches; commit new fixtures)
	cd $(BACKEND) && SERPAPI_MODE=record LLM_MODE=record $(UVICORN)

backend: ## Run only the backend
	cd $(BACKEND) && $(UVICORN)

frontend: ## Run only the frontend
	cd $(FRONTEND) && npm run dev

test: ## Backend tests + frontend typecheck
	cd $(BACKEND) && uv run pytest
	cd $(FRONTEND) && npm run typecheck

lint: ## ruff, format check, eslint, tsc
	cd $(BACKEND) && uv run ruff check . && uv run ruff format --check .
	cd $(FRONTEND) && npm run lint && npm run typecheck

fmt: ## Auto-format and fix the backend
	cd $(BACKEND) && uv run ruff format . && uv run ruff check --fix .

types: ## Export OpenAPI and regenerate frontend/src/api/schema.d.ts
	cd $(BACKEND) && uv run python -m app.export_openapi > openapi.json
	cd $(FRONTEND) && npm run gen:types

reset-db: ## Delete the local SQLite database (recreated on next start)
	rm -f $(BACKEND)/data/*.db
