.DEFAULT_GOAL := help
SHELL := /bin/bash
LOCAL := DevOps/Local

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "};{printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

up: ## Start the local substrate (Postgres, Kafka, Redis, MinIO)
	@$(LOCAL)/docker-all-up.sh

up-all: ## Start everything including observability
	@$(LOCAL)/docker-all-up.sh all

down: ## Stop the local substrate, keep data
	@$(LOCAL)/docker-all-down.sh

status: ## Show what is running and whether it is healthy
	@$(LOCAL)/docker-all-status.sh

logs: ## Tail logs for a stack, e.g. make logs STACK=Kafka
	@$(LOCAL)/docker-all-logs.sh $(or $(STACK),all)

clean: ## Stop and delete all local data
	@$(LOCAL)/docker-all-down.sh all --volumes

reset: ## Destroy and rebuild the local substrate
	@$(LOCAL)/docker-all-reset.sh

seed: ## Load demo tenant, subjects, adapter manifests, policy
	python3 Tools/seed.py

validate: ## Check schemas, taxonomy, and adapter manifests agree
	python3 Tools/validate.py

demo: up seed ## Full local path: substrate, seed, adapter run
	python3 -m Middleware.adapters.sources.directory_watch.handler --once
	python3 Tools/tail.py --max 5

test: ## Run all suites
	python3 -m pytest Middleware/adapters -q || true
	cd Middleware/query-broker && go test ./... || true
	cd Middleware/control-plane && mvn -B -q verify || true

plan: ## Preview how Plan/backlog.yaml projects into the beads graph
	python3 Tools/beads-sync.py --dry-run

plan-apply: ## Create or update beads from Plan/backlog.yaml
	python3 Tools/beads-sync.py

ready: ## Show workable items and why
	bd ready --explain

portals-install: ## Install portal dependencies
	cd Portals/admin-portal && npm ci
	cd Portals/client-portal && npm ci

cdk-synth: ## Synthesize CloudFormation without deploying (free)
	cd DevOps/Cloud/cdk && npm install && npx cdk synth

cdk-diff: ## Diff against a deployed stage
	cd DevOps/Cloud/cdk && npx cdk diff

cdk-destroy: ## Tear down all cloud stacks
	cd DevOps/Cloud/cdk && npx cdk destroy --all --force

.PHONY: help up up-all down status logs clean reset seed validate demo test plan plan-apply ready portals-install cdk-synth cdk-diff cdk-destroy
