@echo off
setlocal enabledelayedexpansion

if "%1"=="" goto :help
if "%1"=="help" goto :help
if "%1"=="test" goto :test
if "%1"=="coverage" goto :coverage
if "%1"=="clean" goto :clean
if "%1"=="docker-build" goto :docker-build
if "%1"=="docker-test" goto :docker-test
goto :help

:help
echo Available commands:
echo   test         Run pytest
echo   coverage     Run tests with coverage report
echo   clean        Clean temporary files and caches
echo   docker-build Build Docker image
echo   docker-test  Run tests inside Docker container
echo   help         Show this help message
goto :end

:test
pytest -v
goto :end

:coverage
pytest --cov=plugins --cov=dags --cov-report=term --cov-report=html
goto :end

:clean
if exist .pytest_cache rmdir /s /q .pytest_cache
if exist .coverage del /f .coverage
if exist htmlcov rmdir /s /q htmlcov
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
goto :end

:docker-build
docker build -t stdev-dag-test -f Dockerfile .
goto :end

:docker-test
call :docker-build
docker run --rm -v %cd%:/app stdev-dag-test pytest -v
goto :end

:end
exit /b 0
