SHELL := /bin/bash 
export PYTHONPATH = .
WORKDIR := .

export LANG = en_US.UTF-8
export LC_ALL = en_US.UTF-8
export LC_CTYPE = en_US.UTF-8
CODEARTIFACT_AUTH_TOKEN := $(shell aws codeartifact get-authorization-token --domain preloop-artifactory-dev --domain-owner 439101250057 --query authorizationToken --output text)

.PHONY: local-install
local-install:
	@poetry config http-basic.preloop_main aws $(CODEARTIFACT_AUTH_TOKEN)
	@poetry config http-basic.pypi-store aws $(CODEARTIFACT_AUTH_TOKEN)
	@poetry update

.PHONY: format
format:
	@echo "### Running isort to PEP-8 compatible sort order"
	poetry run isort .
	@echo "### Running black for PEP-8 compatible files"
	poetry run black .