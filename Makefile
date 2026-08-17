.DEFAULT_GOAL := help

ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../../../..)
COMPOSE := $(ROOT)/bin/docker compose -p college-management-dev -f $(ROOT)/.devcontainer/docker-compose.yml
BENCH := $(COMPOSE) exec -T -w /workspace/development/frappe-bench frappe bench --site college.localhost

.PHONY: help start stop restart status logs migrate test

help:
	@echo "make start    Start the development site"
	@echo "make stop     Stop the development site"
	@echo "make restart  Restart the development site"
	@echo "make status   Show container status"
	@echo "make logs     Follow server logs"
	@echo "make migrate  Run database migrations"
	@echo "make test     Run the app test suite"

start:
	$(COMPOSE) up -d
	@echo "Open http://college.localhost:8000"

stop:
	$(COMPOSE) down

restart: stop start

status:
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs -f server

migrate: start
	$(BENCH) migrate

test: start
	$(BENCH) run-tests --app college_management
