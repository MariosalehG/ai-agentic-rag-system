.PHONY: help setup start stop restart status logs health format lint test test-cov clean pull-model

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

setup:  ## Install Python dependencies
	uv sync

start:  ## Build and start all services
	docker compose -f docker/docker-compose.yml up --build -d

stop:  ## Stop all services
	docker compose -f docker/docker-compose.yml down

restart:  ## Restart all services
	docker compose -f docker/docker-compose.yml restart

status:  ## Show service status
	docker compose -f docker/docker-compose.yml ps

logs:  ## Follow service logs
	docker compose -f docker/docker-compose.yml logs -f

health:  ## Check API health endpoint
	curl -s http://localhost:8000/api/v1/health | python -m json.tool

pull-model:  ## Pull the default local LLM into Ollama
	docker compose -f docker/docker-compose.yml exec ollama ollama pull llama3.2:3b

format:  ## Format and autofix
	uv run ruff format . && uv run ruff check --fix .

lint:  ## Lint and type-check
	uv run ruff check . && uv run mypy src

test:  ## Run tests
	uv run pytest

test-cov:  ## Run tests with coverage
	uv run pytest --cov=src --cov-report=term-missing

clean:  ## Stop services and remove volumes
	docker compose -f docker/docker-compose.yml down --volumes
