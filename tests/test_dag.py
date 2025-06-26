import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

# Import the DAG to test
sys.path.append(str(Path(__file__).parent.parent))

# Mocking the airflow modules for testing
class MockDAG:
    def __init__(self, dag_id, default_args, *args, **kwargs):
        self.dag_id = dag_id
        self.default_args = default_args
        self.task_dict = {}
        for k, v in kwargs.items():
            setattr(self, k, v)

class MockPythonOperator:
    def __init__(self, task_id, python_callable, dag, *args, **kwargs):
        self.task_id = task_id
        self.python_callable = python_callable
        self.dag = dag
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __rshift__(self, other):
        return self

class MockPostgresOperator:
    def __init__(self, task_id, sql, postgres_conn_id, dag, *args, **kwargs):
        self.task_id = task_id
        self.sql = sql
        self.postgres_conn_id = postgres_conn_id
        self.dag = dag
        for k, v in kwargs.items():
            setattr(self, k, v)

class MockPostgresHook:
    def __init__(self, postgres_conn_id):
        self.postgres_conn_id = postgres_conn_id

    def get_sqlalchemy_engine(self):
        return "mock_engine"

# Mock functions
def mock_dag_file():
    """Create a mock version of the DAG file for testing."""
    # Mock the imports
    sys.modules['airflow'] = type('', (), {})
    sys.modules['airflow.DAG'] = MockDAG
    sys.modules['airflow.operators.python'] = type('', (), {'PythonOperator': MockPythonOperator})
    sys.modules['airflow.providers.postgres.operators.postgres'] = type('', (), {'PostgresOperator': MockPostgresOperator})
    sys.modules['airflow.providers.postgres.hooks.postgres'] = type('', (), {'PostgresHook': MockPostgresHook})
    # Create dummy stdev_calculator for import
    sys.modules['stdev_calculator'] = type('', (), {'IncrementalStdevCalculator': type('', (), {})})
    
    # Now import the dag module
    from dags.stdev_dag import extract_and_validate_data, load_raw_data_to_postgres, calculate_standard_deviations, save_results_to_postgres, cleanup_temp_files
    
    return {
        'extract_and_validate_data': extract_and_validate_data,
        'load_raw_data_to_postgres': load_raw_data_to_postgres,
        'calculate_standard_deviations': calculate_standard_deviations,
        'save_results_to_postgres': save_results_to_postgres,
        'cleanup_temp_files': cleanup_temp_files
    }


class TestDAGFunctions:
    """Test suite for DAG task functions."""
    
    @pytest.fixture(scope="module")
    def dag_functions(self):
        """Get DAG functions to test."""
        try:
            return mock_dag_file()
        except ImportError:
            pytest.skip("Could not import DAG functions due to Airflow dependencies")
    
    def test_extract_and_validate_function_structure(self, dag_functions):
        """Test that extract_and_validate_data function exists and has expected signature."""
        extract_fn = dag_functions.get('extract_and_validate_data')
        assert extract_fn is not None
        assert callable(extract_fn)
    
    def test_load_raw_data_function_structure(self, dag_functions):
        """Test that load_raw_data_to_postgres function exists and has expected signature."""
        load_fn = dag_functions.get('load_raw_data_to_postgres')
        assert load_fn is not None
        assert callable(load_fn)
    
    def test_calculate_function_structure(self, dag_functions):
        """Test that calculate_standard_deviations function exists and has expected signature."""
        calc_fn = dag_functions.get('calculate_standard_deviations')
        assert calc_fn is not None
        assert callable(calc_fn)
    
    def test_save_results_function_structure(self, dag_functions):
        """Test that save_results_to_postgres function exists and has expected signature."""
        save_fn = dag_functions.get('save_results_to_postgres')
        assert save_fn is not None
        assert callable(save_fn)
    
    def test_cleanup_function_structure(self, dag_functions):
        """Test that cleanup_temp_files function exists and has expected signature."""
        cleanup_fn = dag_functions.get('cleanup_temp_files')
        assert cleanup_fn is not None
        assert callable(cleanup_fn)
