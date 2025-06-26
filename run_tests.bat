@echo off
echo Running tests for stdev_dag project...

:: Check if pytest is installed
pip show pytest >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing pytest...
    pip install pytest
)

:: Run the tests
echo Running unit tests...
pytest

echo.
echo Testing complete!
