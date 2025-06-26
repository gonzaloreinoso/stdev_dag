# PowerShell Development Scripts for Standard Deviation DAG Project

# Setup development environment
function Setup-Dev {
    Write-Host "Setting up development environment..." -ForegroundColor Green
    pip install -r requirements.txt -r requirements-dev.txt
    pre-commit install
    New-Item -ItemType Directory -Force -Path data, results, logs
    Write-Host "Development environment ready!" -ForegroundColor Green
}

# Run all tests
function Test-All {
    Write-Host "Running unit tests..." -ForegroundColor Yellow
    pytest tests/unit/ -v --cov=plugins --cov-report=term --cov-report=html
    
    Write-Host "Running integration tests..." -ForegroundColor Yellow
    pytest tests/integration/ -v -m integration
}

# Run unit tests only
function Test-Unit {
    pytest tests/unit/ -v --cov=plugins --cov-report=term --cov-report=html
}

# Run integration tests only
function Test-Integration {
    pytest tests/integration/ -v -m integration
}

# Code quality checks
function Check-Quality {
    Write-Host "Checking code formatting..." -ForegroundColor Yellow
    black --check --diff .
    isort --check-only --diff .
    
    Write-Host "Running linting..." -ForegroundColor Yellow
    flake8 plugins/ dags/ tests/
    mypy plugins/ dags/ --ignore-missing-imports
}

# Format code
function Format-Code {
    Write-Host "Formatting code..." -ForegroundColor Yellow
    black .
    isort .
}

# Security scans
function Test-Security {
    Write-Host "Running security scans..." -ForegroundColor Yellow
    bandit -r plugins/ dags/ -f json -o bandit-report.json
    safety check --json --output safety-report.json
}

# Run all CI checks locally
function Test-CI {
    Write-Host "Running all CI checks..." -ForegroundColor Green
    Check-Quality
    Test-All
    Test-Security
    Write-Host "All CI checks passed!" -ForegroundColor Green
}

# Docker operations
function Start-Docker {
    Write-Host "Starting Docker containers..." -ForegroundColor Green
    docker-compose up -d
}

function Stop-Docker {
    Write-Host "Stopping Docker containers..." -ForegroundColor Yellow
    docker-compose down
}

function Build-Docker {
    Write-Host "Building Docker image..." -ForegroundColor Green
    docker build -t stdev-dag:latest .
}

# Database operations
function Connect-Database {
    docker-compose exec postgres psql -U airflow -d airflow
}

function Init-Airflow {
    Write-Host "Initializing Airflow..." -ForegroundColor Green
    docker-compose exec airflow-webserver airflow db init
    docker-compose exec airflow-webserver airflow users create --username admin --firstname Admin --lastname User --role Admin --email admin@example.com --password admin
}

# Check health
function Check-Health {
    Write-Host "Checking Docker containers..." -ForegroundColor Yellow
    docker-compose ps
    
    Write-Host "`nChecking Airflow webserver..." -ForegroundColor Yellow
    try {
        Invoke-WebRequest -Uri "http://localhost:8080/health" -Method Get
        Write-Host "Airflow webserver is healthy" -ForegroundColor Green
    } catch {
        Write-Host "Airflow webserver not responding" -ForegroundColor Red
    }
    
    Write-Host "`nChecking database..." -ForegroundColor Yellow
    docker-compose exec postgres pg_isready -U airflow
}

# Performance benchmark
function Test-Performance {
    Write-Host "Running performance benchmark..." -ForegroundColor Yellow
    python -c "
import time
from plugins.stdev_calculator import IncrementalStdevCalculator
calc = IncrementalStdevCalculator('data/stdev_price_data.parq.gzip')
calc.load_data()
start = time.time()
results = calc.process('2021-11-20', '2021-11-22')
duration = time.time() - start
print(f'Processed {len(results)} records in {duration:.3f} seconds')
"
}

# Clean up
function Clean-All {
    Write-Host "Cleaning up temporary files..." -ForegroundColor Yellow
    Get-ChildItem -Recurse -Name "*.pyc" | Remove-Item -Force
    Get-ChildItem -Recurse -Name "__pycache__" -Directory | Remove-Item -Recurse -Force
    Get-ChildItem -Name "*.coverage" | Remove-Item -Force
    Get-ChildItem -Name "htmlcov" -Directory | Remove-Item -Recurse -Force
    Get-ChildItem -Name ".pytest_cache" -Directory | Remove-Item -Recurse -Force
    Get-ChildItem -Name ".mypy_cache" -Directory | Remove-Item -Recurse -Force
    Remove-Item -Force -ErrorAction SilentlyContinue bandit-report.json, safety-report.json
}

# Show help
function Show-Help {
    Write-Host @"
Available commands:
  Setup-Dev         - Setup development environment
  Test-All          - Run all tests
  Test-Unit         - Run unit tests only
  Test-Integration  - Run integration tests only
  Check-Quality     - Run code quality checks
  Format-Code       - Format code with black and isort
  Test-Security     - Run security scans
  Test-CI           - Run all CI checks locally
  Start-Docker      - Start Docker containers
  Stop-Docker       - Stop Docker containers
  Build-Docker      - Build Docker image
  Connect-Database  - Connect to PostgreSQL database
  Init-Airflow      - Initialize Airflow
  Check-Health      - Check application health
  Test-Performance  - Run performance benchmark
  Clean-All         - Clean up temporary files
  Show-Help         - Show this help message

Usage examples:
  Setup-Dev
  Test-CI
  Start-Docker
  Check-Health
"@ -ForegroundColor Cyan
}

# Export functions
Export-ModuleMember -Function *
