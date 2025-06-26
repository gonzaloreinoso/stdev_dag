.PHONY: test coverage clean docker-test docker-build help

help:
	@echo "Available commands:"
	@echo "  test         Run pytest"
	@echo "  coverage     Run tests with coverage report"
	@echo "  clean        Clean temporary files and caches"
	@echo "  docker-test  Run tests inside Docker container"
	@echo "  docker-build Build Docker image"
	@echo "  help         Show this help message"

test:
	pytest -v

coverage:
	pytest --cov=plugins --cov=dags --cov-report=term --cov-report=html

clean:
	rm -rf .pytest_cache .coverage htmlcov
	find . -name "__pycache__" -exec rm -rf {} +

docker-build:
	docker build -t stdev-dag-test -f Dockerfile .

docker-test: docker-build
	docker run --rm -v $(shell pwd):/app stdev-dag-test pytest -v
