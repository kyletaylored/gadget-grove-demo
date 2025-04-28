# Makefile for GadgetGrove ETL project

# --- Git metadata ---
GIT_COMMIT_SHA := $(shell git rev-parse HEAD 2>/dev/null || echo "unknown")
GIT_SHORT_SHA := $(shell git rev-parse --short HEAD 2>/dev/null || echo "latest")
GIT_REPO_URL := $(shell git config --get remote.origin.url 2>/dev/null || echo "unknown")

# --- Build arguments ---
BUILD_ARGS := \
	--build-arg GIT_COMMIT_SHA=$(GIT_COMMIT_SHA) \
	--build-arg GIT_REPOSITORY_URL=$(GIT_REPO_URL) \
	--build-arg DD_VERSION=$(GIT_SHORT_SHA) \
	--build-arg IMAGE_TAG=$(GIT_SHORT_SHA)

# Docker Compose shortcut
DC := docker compose

# --- Targets ---
.PHONY: help build up down restart logs tail bash dbt clean nuke rebuild env

help:
	@echo "Available targets:"
	@echo "  make build     - Build all Docker images with Git metadata and version tags"
	@echo "  make up        - Start all services"
	@echo "  make down      - Stop all services"
	@echo "  make restart   - Restart services"
	@echo "  make logs      - Show logs for all services"
	@echo "  make tail      - Tail logs continuously"
	@echo "  make bash      - Get a shell into the web container"
	@echo "  make dbt       - Run dbt CLI inside the container"
	@echo "  make clean     - Stop services, remove project volumes and images"
	@echo "  make nuke      - Remove ALL docker resources (containers, images, volumes, networks)"
	@echo "  make rebuild   - Clean, rebuild, and bring services up in one command"
	@echo "  make env       - Show detected environment variables and settings"

build:
	@echo "Building services with Git metadata..."
	@echo "Git Commit: $(GIT_COMMIT_SHA)"
	@echo "Repo URL:   $(GIT_REPO_URL)"
	@echo "Version Tag: $(GIT_SHORT_SHA)"
	$(DC) build $(BUILD_ARGS)

up: 
	$(DC) up -d

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

clean:
	@echo "Stopping and removing project containers, volumes, and networks..."
	$(DC) down -v --remove-orphans
	@echo "Removing dangling images..."
	@docker image prune -f
	@echo "Done cleaning up project-specific Docker artifacts."

nuke:
	@echo "WARNING: This will DELETE ALL containers, images, volumes, networks on your machine!"
	@docker system prune -a --volumes -f
	@echo "Docker system fully nuked."

rebuild: clean build up
	@echo "Rebuild complete!"

env:
	@echo "Current Project Environment"
	@echo "------------------------------"
	@echo "Git Repository URL: $(GIT_REPO_URL)"
	@echo "Git Commit SHA:     $(GIT_COMMIT_SHA)"
	@echo "Git Short SHA:      $(GIT_SHORT_SHA)"
	@echo "Docker Compose File: docker-compose.yml"
	@echo "Docker Compose Version: $$(docker compose version --short || echo 'unknown')"
	@echo "Docker Version: $$(docker --version | awk '{print $$3}' | sed 's/,//g')"
	@echo "User: $$(whoami)"
	@echo "Host: $$(hostname)"
	@echo "PWD: $(shell pwd)"
