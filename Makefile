# SUPMEAL - Makefile
# Aide-memoire pour les commandes courantes

.PHONY: help up down restart logs build rebuild clean test lint format shell-api shell-db seed

help: ## Afficher cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

up: ## Demarrer tous les services (build + up)
	docker compose up -d --build

down: ## Arreter tous les services
	docker compose down

restart: ## Redemarrer tous les services
	docker compose restart

logs: ## Suivre les logs
	docker compose logs -f

build: ## Builder les images
	docker compose build

rebuild: ## Reconstruire le serveur from scratch
	docker compose down
	docker volume rm supmeal_pgdata 2>/dev/null || true
	docker compose build --no-cache server
	docker compose up -d

clean: ## Arreter et supprimer volumes (PERTE DE DONNEES)
	docker compose down -v

test: ## Lancer les tests backend
	cd server && python -m pytest -v

lint: ## Linter Python (ruff)
	cd server && ruff check app/

format: ## Formater le code (ruff)
	cd server && ruff format app/

shell-api: ## Shell dans le conteneur API
	docker compose exec server bash

shell-db: ## Console PostgreSQL
	docker compose exec db psql -U supmeal -d supmeal

seed: ## Creer un utilisateur de demo
	docker compose exec server python -c "from app.db.session import *; from app.models.user import User, AuthProvider; from app.core.security import hash_password; print('TODO')"