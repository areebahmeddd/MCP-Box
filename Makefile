.PHONY: help
.DEFAULT_GOAL := help

CYAN   := \033[0;36m
GREEN  := \033[0;32m
YELLOW := \033[0;33m
RED    := \033[0;31m
RESET  := \033[0m

help:
	@echo '$(CYAN)SuperBox Backend$(RESET)'
	@echo ''
	@echo 'Usage: make $(YELLOW)<target>$(RESET)'
	@echo ''
	@echo '  $(YELLOW)Setup:$(RESET)'
	@echo '    install               - Install all Python dependencies'
	@echo '    install-dev           - Install with dev tools (pytest, ruff, pre-commit)'
	@echo ''
	@echo '  $(YELLOW)Testing:$(RESET)'
	@echo '    test                  - Run all tests (Python + Go)'
	@echo '    test-py               - Run Python tests with coverage'
	@echo '    test-go               - Run Go handler tests'
	@echo ''
	@echo '  $(YELLOW)Server:$(RESET)'
	@echo '    run                   - Run Go server locally'
	@echo '    build                 - Build Go server binary'
	@echo ''
	@echo '  $(YELLOW)Docker:$(RESET)'
	@echo '    up                    - Build and start server via Docker Compose'
	@echo '    down                  - Stop and remove containers'
	@echo '    logs                  - Tail container logs'
	@echo '    watch                 - Start with hot reload (sync + rebuild)'
	@echo ''
	@echo '  $(YELLOW)Code Quality:$(RESET)'
	@echo '    lint                  - Check formatting and run linter (ruff)'
	@echo '    format                - Auto-fix formatting'
	@echo ''
	@echo '  $(YELLOW)Cleanup:$(RESET)'
	@echo '    clean                 - Remove build artifacts'

# ============================================
# Setup
# ============================================

.PHONY: install install-dev

install:
	@echo "$(CYAN)Installing dependencies...$(RESET)"
	pip install .

install-dev:
	@echo "$(CYAN)Installing dependencies with dev tools...$(RESET)"
	pip install -e .[dev]

# ============================================
# Testing
# ============================================

.PHONY: test test-py test-go

test: test-py test-go
	@echo "$(GREEN)All tests passed!$(RESET)"

test-py:
	@echo "$(CYAN)Running Python tests...$(RESET)"
	pytest -q --tb=short --cov=superbox --cov-report=term-missing

test-go:
	@echo "$(CYAN)Running Go tests...$(RESET)"
	cd src/superbox/server && go test ./handlers/... -v

# ============================================
# Server
# ============================================

.PHONY: run build

run:
	@echo "$(CYAN)Starting Go server...$(RESET)"
	cd src/superbox/server && go run .

build:
	@echo "$(CYAN)Building Go server binary...$(RESET)"
	cd src/superbox/server && CGO_ENABLED=0 go build -ldflags="-s -w" -o server .
	@echo "$(GREEN)Binary: src/superbox/server/server$(RESET)"

# ============================================
# Docker
# ============================================

.PHONY: up down logs watch

up:
	@echo "$(CYAN)Starting Docker Compose...$(RESET)"
	docker compose up -d --build

down:
	@echo "$(CYAN)Stopping Docker Compose...$(RESET)"
	docker compose down

logs:
	docker compose logs -f

watch:
	@echo "$(CYAN)Starting with hot reload...$(RESET)"
	docker compose watch

# ============================================
# Code Quality
# ============================================

.PHONY: lint format

lint:
	@echo "$(CYAN)Checking formatting and linting...$(RESET)"
	ruff format --check .
	ruff check .
	@echo "$(GREEN)All checks passed!$(RESET)"

format:
	@echo "$(CYAN)Auto-fixing formatting...$(RESET)"
	ruff format .
	ruff check --fix .

# ============================================
# Cleanup
# ============================================

.PHONY: clean

clean:
	@echo "$(CYAN)Cleaning build artifacts...$(RESET)"
	rm -f src/superbox/server/server src/superbox/server/server.exe
	rm -rf dist/ *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	docker compose down --volumes --remove-orphans 2>/dev/null || true
	@echo "$(GREEN)Clean!$(RESET)"
