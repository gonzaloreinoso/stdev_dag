# Makefile for Standard Deviation DAG Project
.PHONY: help install install-dev test test-unit test-integration lint format security clean docker-build docker-run setup-dev

# Default target
help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Installation
install: ## Install production dependencies
	pip install -r requirements.txt

install-dev: ## Install development dependencies
	pip install -r requirements.txt -r requirements-dev.txt
	pre-commit install

# Testing
test: test-unit test-integration ## Run all tests

test-unit: ## Run unit tests
	pytest tests/unit/ -v --cov=plugins --cov-report=term --cov-report=html

test-integration: ## Run integration tests (requires database)
	pytest tests/integration/ -v -m integration

test-dag: ## Test DAG validation
	pytest tests/unit/test_dag_validation.py -v

# Code Quality
lint: ## Run linting checks
	flake8 plugins/ dags/ tests/
	mypy plugins/ dags/ --ignore-missing-imports

format: ## Format code with black and isort
	black .
	isort .

format-check: ## Check code formatting
	black --check --diff .
	isort --check-only --diff .

# Security
security: ## Run security scans
	bandit -r plugins/ dags/ -f json -o bandit-report.json
	safety check --json --output safety-report.json

security-report: ## Generate security report
	@echo "=== Security Scan Results ==="
	@echo "Bandit (Python Security):"
	@bandit -r plugins/ dags/ || true
	@echo "\nSafety (Known Vulnerabilities):"
	@safety check || true

# Docker
docker-build: ## Build Docker image
	docker build -t stdev-dag:latest .

docker-build-dev: ## Build Docker image for development
	docker build -t stdev-dag:dev --target builder .

docker-run: ## Run Docker container locally
	docker-compose up -d

docker-stop: ## Stop Docker containers
	docker-compose down

docker-logs: ## View Docker container logs
	docker-compose logs -f

# Development Environment
setup-dev: install-dev ## Setup development environment
	@echo "Setting up development environment..."
	@echo "Installing pre-commit hooks..."
	pre-commit install
	@echo "Creating necessary directories..."
	mkdir -p data results logs
	@echo "Development environment ready!"

# Database
db-init: ## Initialize database (requires running containers)
	docker-compose exec postgres psql -U airflow -d airflow -f /docker-entrypoint-initdb.d/01-init-db.sql

db-connect: ## Connect to database
	docker-compose exec postgres psql -U airflow -d airflow

db-backup: ## Backup database
	docker-compose exec postgres pg_dump -U airflow airflow > backup_$$(date +%Y%m%d_%H%M%S).sql

# Airflow
airflow-init: ## Initialize Airflow (requires running containers)
	docker-compose exec airflow-webserver airflow db init
	docker-compose exec airflow-webserver airflow users create \
		--username admin \
		--firstname Admin \
		--lastname User \
		--role Admin \
		--email admin@example.com \
		--password admin

airflow-test-dag: ## Test DAG execution
	docker-compose exec airflow-webserver airflow dags test stdev_calculation_pipeline 2021-11-20

# Data Processing
generate-sample-data: ## Generate sample data for testing
	python generate_sample_data.py

process-local: ## Run calculation locally (without Airflow)
	python -c "
	from plugins.stdev_calculator import IncrementalStdevCalculator;
	calc = IncrementalStdevCalculator('data/stdev_price_data.parq.gzip', state_path='results/test_state.json');
	calc.load_data();
	results = calc.process('2021-11-20', '2021-11-22');
	print(f'Processed {len(results)} records');
	calc.save(results, 'results/test_results.csv');
	print('Results saved to results/test_results.csv')
	"

# Cleanup
clean: ## Clean up temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.coverage" -delete
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	rm -f bandit-report.json safety-report.json

clean-docker: ## Clean up Docker resources
	docker-compose down -v
	docker system prune -f
	docker volume prune -f

# Performance
benchmark: ## Run performance benchmark
	python -c "
	import time;
	from plugins.stdev_calculator import IncrementalStdevCalculator;
	calc = IncrementalStdevCalculator('data/stdev_price_data.parq.gzip');
	calc.load_data();
	start = time.time();
	results = calc.process('2021-11-20', '2021-11-22');
	duration = time.time() - start;
	print(f'Processed {len(results)} records in {duration:.3f} seconds')
	"

# Monitoring
check-health: ## Check application health
	@echo "Checking Docker containers..."
	docker-compose ps
	@echo "\nChecking Airflow webserver..."
	curl -f http://localhost:8080/health || echo "Airflow webserver not responding"
	@echo "\nChecking database..."
	docker-compose exec postgres pg_isready -U airflow || echo "Database not ready"

logs: ## View application logs
	docker-compose logs -f --tail=100

# CI/CD
ci-local: format-check lint test security ## Run CI checks locally
	@echo "All CI checks passed!"

pre-commit: ## Run pre-commit hooks
	pre-commit run --all-files

# Release
tag-release: ## Tag a new release (usage: make tag-release VERSION=v1.0.0)
	@if [ -z "$(VERSION)" ]; then echo "Usage: make tag-release VERSION=v1.0.0"; exit 1; fi
	git tag -a $(VERSION) -m "Release $(VERSION)"
	git push origin $(VERSION)
	@echo "Tagged release $(VERSION)"

# Documentation
docs: ## Generate documentation
	@echo "Documentation available in docs/ directory"
	@echo "CI/CD Guide: docs/CI_CD_GUIDE.md"
	@echo "README: README.md"

# Environment specific commands
dev-up: ## Start development environment
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

staging-deploy: ## Deploy to staging (requires proper setup)
	@echo "Deploying to staging..."
	# Add staging deployment commands here

prod-deploy: ## Deploy to production (requires proper setup)
	@echo "Deploying to production..."
	# Add production deployment commands here
