# Testing Documentation

This directory contains tests for the Standard Deviation Calculation DAG project.

## Test Structure

- **Unit Tests**: Tests for individual components like the `IncrementalStdevCalculator` class
- **DAG Tests**: Tests for the Airflow DAG structure and tasks (requires mocking)
- **Integration Tests**: End-to-end workflow tests

## Running Tests

To run all tests:
```bash
pytest
```

To run specific test files:
```bash
pytest tests/test_calculator.py
pytest tests/test_integration.py
```

To run with verbose output:
```bash
pytest -v
```

## Test Files

1. **test_calculator.py**: Tests for the `IncrementalStdevCalculator` class
   - Initialization
   - Data loading
   - State management
   - Standard deviation calculation
   - Gap detection

2. **test_dag.py**: Tests for the DAG structure
   - Task function structure validation
   - DAG dependency verification
   
3. **test_integration.py**: Integration tests
   - Full workflow simulation
   - State persistence across runs
   - Results validation

## Test Configuration

- **conftest.py**: Contains pytest fixtures for:
  - Test data generation
  - Temporary file paths
  - Result storage

- **pytest.ini**: Contains pytest configuration

## Test Dependencies

The test suite requires:
- pytest
- pandas
- numpy
- tempfile (built-in)
- pathlib (built-in)

These dependencies are included in the main requirements.txt file.
