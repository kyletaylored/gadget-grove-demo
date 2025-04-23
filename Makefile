# Makefile for GadgetGrove ETL project

# Git metadata (auto-detected)
GIT_COMMIT_SHA := $(shell git rev-parse HEAD 2>/dev/null || echo "unknown")
GIT_SHORT_SHA := $(shell git rev-parse --short HEAD 2>/dev/null || echo "latest")
GIT_REPO_URL := $(shell git config --get remote.origin.url 2>/dev/null || echo "unknown")

# Build args
BUILD_ARGS := \
	--build-arg GIT_COMMIT_SHA=$(GIT_COMMIT_SHA) \
	--build-arg GIT_REPOSITORY_URL=$(GIT_REPO_URL) \
	--build-arg DD_VERSION=$(GIT_SHORT_SHA)

# Docker Compose
DC := docker compose

.PHONY: help build up down restart logs tail bash dbt

help:
	@echo "Available targets:"
	@echo "  make build     - Build all Docker images with Git metadata"
	@echo "  make up        - Start all services (with rebuild)"
	@echo "  make down      - Stop all services"
	@echo "  make restart   - Restart services"
	@echo "  make logs      - Show logs for all services"
	@echo "  make tail      - Tail logs continuously"
	@echo "  make bash      - Get a shell into the web container"
	@echo "  make dbt       - Run dbt CLI inside the container"

build:
	@echo "🚀 Building services with Git metadata..."
	@echo "🔧 Git Commit: $(GIT_COMMIT_SHA)"
	@echo "🔗 Repo URL:   $(GIT_REPO_URL)"
	@echo "🧪 Datadog Version Tag: $(GIT_SHORT_SHA)"
	$(DC) build $(BUILD_ARGS)

up: build
	$(DC) up

down:
	$(DC) down

restart: down up

logs:
	$(DC) logs --no-color

tail:
	$(DC) logs -f

bash:
	$(DC) exec webapp bash

dbt:
	$(DC) exec prefect-agent dbt run --project-dir /opt/dbt --profiles-dir /opt/dbt
