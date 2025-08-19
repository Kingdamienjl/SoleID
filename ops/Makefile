SHELL := /usr/bin/bash
COMPOSE := docker compose -f ops/docker-compose.yml

.PHONY: up down logs seed reindex

up:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down -v

logs:
	$(COMPOSE) logs -f --tail=200 | cat

seed:
	PYTHONPATH=backend python scripts/bootstrap_catalog.py

reindex:
	PYTHONPATH=backend python scripts/rebuild_index.py
