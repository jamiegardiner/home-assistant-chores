.DEFAULT_GOAL := help

VENV     := .venv
UV       := uv
MD_FILES := $(shell git ls-files "*.md" | grep -v "^CHANGELOG.md$$")

.PHONY: help venv venv-destroy install test typecheck lint format translations check up down stop start logs

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

typecheck: ## Run mypy type checking (first-party source only — tests aren't strictly typed)
	$(UV) run mypy custom_components scripts

lint: ## Check code with ruff (linter — catches bugs and style issues)
	$(UV) run ruff check .

format: ## Auto-fix formatting (ruff format, ruff check --fix, mdformat) and lint issues where possible
	$(UV) run ruff format .
	$(UV) run ruff check --fix .
	$(UV) run mdformat $(MD_FILES)

translations: ## Check that strings.json and translations/en.json have identical key paths
	$(UV) run python scripts/check_translations.py

check: ## Check code (read-only): lint, format, typecheck, markdown, translations, tests — mirrors CI
	$(UV) run ruff check .
	$(UV) run ruff format --check .
	$(UV) run mypy custom_components scripts
	$(UV) run mdformat --check $(MD_FILES)
	$(UV) run python scripts/check_translations.py
	$(UV) run pytest

# ── Docker ─────────────────────────────────────────────────────────────────────

up: ## Start Home Assistant in Docker
	docker compose up -d

down: ## Stop and remove Home Assistant container
	docker compose down

stop: ## Pause Home Assistant container (preserves container state)
	docker compose stop

start: ## Resume a paused Home Assistant container
	docker compose start

logs: ## Tail Home Assistant logs
	docker compose logs -f homeassistant