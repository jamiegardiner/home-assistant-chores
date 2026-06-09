.DEFAULT_GOAL := help

VENV := .venv
UV   := uv

.PHONY: help venv venv-destroy install test typecheck lint format check up down destroy logs

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

# ── Virtual environment ────────────────────────────────────────────────────────

venv: ## Create .venv and install dependencies
	$(UV) venv $(VENV)
	$(UV) pip install -r requirements_test.txt
	@echo ""
	@echo "Done. To activate in your shell:"
	@echo "  source $(VENV)/bin/activate"
	@echo ""
	@echo "To deactivate, run:  deactivate"

venv-destroy: ## Delete the .venv directory
	rm -rf $(VENV)
	@echo "$(VENV) removed."

install: ## Sync dependencies into the existing venv
	$(UV) pip install -r requirements_test.txt

# ── Code quality ───────────────────────────────────────────────────────────────

test: ## Run the test suite
	$(UV) run pytest

typecheck: ## Run mypy type checking
	$(UV) run mypy custom_components/chores

lint: ## Check code with ruff (linter — catches bugs and style issues)
	$(UV) run ruff check custom_components tests

format: ## Auto-format code with ruff
	$(UV) run ruff format custom_components tests

check: lint typecheck test ## Run lint + typecheck + tests

# ── Docker ─────────────────────────────────────────────────────────────────────

up: ## Start Home Assistant in Docker
	docker compose up -d

down: ## Stop Home Assistant (keeps data)
	docker compose down

destroy: ## Stop Home Assistant and remove all volumes
	docker compose down -v

logs: ## Tail Home Assistant logs
	docker compose logs -f homeassistant