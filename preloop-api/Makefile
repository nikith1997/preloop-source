SHELL := /bin/bash
export PYTHONPATH := $(shell pwd)/src
WORKDIR := .
CODEARTIFACT_AUTH_TOKEN := $(shell aws codeartifact get-authorization-token --domain preloop-artifactory-dev --domain-owner 439101250057 --query authorizationToken --output text)

.PHONY: local-install
local-install:
	@poetry config http-basic.preloop_main aws $(CODEARTIFACT_AUTH_TOKEN)
	@poetry config http-basic.pypi-store aws $(CODEARTIFACT_AUTH_TOKEN)
	@poetry update

.PHONY: start-shell
start-shell:
	@echo "Starting shell"
	@poetry shell

.PHONY: initial-migration
initial-migration:
	@echo "Running migrations"
	@source "$(shell poetry env list --full-path | grep Activated | cut -d' ' -f1)/bin/activate"
	@alembic upgrade head

.PHONY: migrate
migrate:
	@if [ "$$(poetry run alembic check)" = "No new upgrade operations detected." ]; then \
		echo "No new migrations"; \
	else \
		echo "Running migrations"; \
		alembic revision --autogenerate; \
		alembic upgrade head; \
	fi

.PHONY: start-server
start-server:
	@echo "Starting server"
	@poetry run uvicorn src.main:app --reload

.PHONY: format
format:
	@echo "### Running isort to PEP-8 compatible sort order"
	poetry run isort .
	@echo "### Running black for PEP-8 compatible files"
	poetry run black .
