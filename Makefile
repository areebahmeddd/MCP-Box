# ============================================
# Setup
# ============================================

.PHONY: install install-dev

install:
	@echo "Installing dependencies..."
	pip install .

install-dev:
	@echo "Installing dependencies with dev tools..."
	pip install -e .[dev]

# ============================================
# Testing
# ============================================

.PHONY: test test-py test-go

test: test-py test-go
	@echo "All tests passed!"

test-py:
	@echo "Running Python tests..."
	pytest -q --tb=short --cov=superbox --cov-report=term-missing

test-go:
	@echo "Running Go tests..."
	cd src/superbox/server && go test ./handlers/... -v

# ============================================
# Server
# ============================================

.PHONY: run build

run:
	@echo "Starting Go server..."
	cd src/superbox/server && go run .

build:
	@echo "Building Go server binary..."
	cd src/superbox/server && CGO_ENABLED=0 go build -ldflags="-s -w" -o server .
	@echo "Binary: src/superbox/server/server"

# ============================================
# Docker
# ============================================

.PHONY: up down logs watch

up:
	@echo "Starting Docker Compose..."
	docker compose up -d --build

down:
	@echo "Stopping Docker Compose..."
	docker compose down

logs:
	docker compose logs -f

watch:
	@echo "Starting with hot reload..."
	docker compose watch

# ============================================
# Code Quality
# ============================================

.PHONY: lint format

lint:
	@echo "Checking formatting and linting..."
	ruff format --check .
	ruff check .
	@echo "All checks passed!"

format:
	@echo "Auto-fixing formatting..."
	ruff format .
	ruff check --fix .

# ============================================
# Cleanup
# ============================================

.PHONY: clean

clean:
	@echo "Cleaning build artifacts..."
	rm -f src/superbox/server/server src/superbox/server/server.exe
	rm -rf dist/ *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	docker compose down --volumes --remove-orphans 2>/dev/null || true
	@echo "Clean!"
