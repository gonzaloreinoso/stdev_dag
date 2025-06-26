"""
Pytest configuration file for the stdev_dag project.
"""
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest
from sqlalchemy import create_engine


@pytest.fixture
def sample_price_data():
    """Create sample price data for testing."""
    data = {
        'security_id': ['SEC1', 'SEC1', 'SEC1', 'SEC2', 'SEC2', 'SEC2'] * 10,
        'snap_time': pd.date_range('2021-11-20 10:00:00', periods=60, freq='H'),
        'bid': [100.0, 100.1, 100.2, 200.0, 200.1, 200.2] * 10,
        'mid': [100.5, 100.6, 100.7, 200.5, 200.6, 200.7] * 10,
        'ask': [101.0, 101.1, 101.2, 201.0, 201.1, 201.2] * 10,
    }
    return pd.DataFrame(data)


@pytest.fixture
def temp_parquet_file(sample_price_data):
    """Create a temporary parquet file with sample data."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.parq') as f:
        sample_price_data.to_parquet(f.name)
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def temp_state_file():
    """Create a temporary state file path."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as f:
        yield f.name
    if os.path.exists(f.name):
        os.unlink(f.name)


@pytest.fixture
def temp_dir():
    """Create a temporary directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_postgres_hook():
    """Mock PostgresHook for testing."""
    mock_hook = MagicMock()
    mock_engine = MagicMock()
    mock_hook.get_sqlalchemy_engine.return_value = mock_engine
    return mock_hook


@pytest.fixture
def test_database_url():
    """Database URL for integration tests."""
    return os.getenv('DATABASE_URL', 'postgresql://airflow:airflow@localhost:5432/airflow')


@pytest.fixture
def test_db_engine(test_database_url):
    """Create a test database engine."""
    try:
        engine = create_engine(test_database_url)
        yield engine
    except Exception:
        pytest.skip("Test database not available")


# Configure pytest options
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires database)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
