"""Integration tests for the complete pipeline."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest
from airflow.models import DagBag

from plugins.stdev_calculator import IncrementalStdevCalculator


class TestPipelineIntegration:
    """Integration tests for the complete standard deviation calculation pipeline."""

    @pytest.fixture
    def sample_market_data(self):
        """Create realistic market data for integration testing."""
        # Create 3 days of hourly data for 2 securities
        timestamps = pd.date_range(
            start="2023-01-01 09:00:00",
            end="2023-01-03 16:00:00",
            freq="h"
        )
        
        data = []
        for security_id in ["AAPL", "GOOGL"]:
            base_price = 150.0 if security_id == "AAPL" else 2800.0
            
            for ts in timestamps:
                price_change = (hash(str(ts) + security_id) % 100 - 50) / 100.0
                mid_price = base_price + price_change
                
                data.append({
                    "security_id": security_id,
                    "snap_time": ts,
                    "bid": mid_price - 0.05,
                    "mid": mid_price,
                    "ask": mid_price + 0.05
                })
        
        return pd.DataFrame(data)

    @pytest.fixture
    def temp_data_files(self, sample_market_data):
        """Create temporary data files for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            data_path = Path(temp_dir) / "test_data.parq"
            state_path = Path(temp_dir) / "test_state.json"
            results_path = Path(temp_dir) / "test_results.csv"
            
            sample_market_data.to_parquet(data_path)
            
            yield {
                "data_path": data_path,
                "state_path": state_path,
                "results_path": results_path
            }

    def test_full_pipeline_execution(self, temp_data_files):
        """Test the complete pipeline from data loading to results saving."""
        calculator = IncrementalStdevCalculator(
            price_path=temp_data_files["data_path"],
            window_size=5,
            state_path=temp_data_files["state_path"]
        )
        
        # Step 1: Load data
        calculator.load_data()
        assert calculator.df is not None
        assert len(calculator.df) > 0
        
        # Step 2: Process data
        start_time = "2023-01-02 10:00:00"
        end_time = "2023-01-02 15:00:00"
        
        results = calculator.process(start_time, end_time)
        
        # Verify results structure
        assert isinstance(results, pd.DataFrame)
        if not results.empty:
            expected_columns = [
                "security_id", "timestamp", "bid_stdev", "mid_stdev", "ask_stdev"
            ]
            assert all(col in results.columns for col in expected_columns)
            
            # Check that we have results for both securities
            securities = results["security_id"].unique()
            assert len(securities) > 0
            
            # Check timestamp range
            result_timestamps = results["timestamp"]
            assert result_timestamps.min() >= pd.Timestamp(start_time)
            assert result_timestamps.max() <= pd.Timestamp(end_time)
        
        # Step 3: Save results
        calculator.save(results, temp_data_files["results_path"])
        assert temp_data_files["results_path"].exists()
        
        # Step 4: Verify state persistence
        assert temp_data_files["state_path"].exists()

    def test_incremental_processing(self, temp_data_files):
        """Test that incremental processing maintains state correctly."""
        calculator = IncrementalStdevCalculator(
            price_path=temp_data_files["data_path"],
            window_size=3,
            state_path=temp_data_files["state_path"]
        )
        
        calculator.load_data()
        
        # First processing run
        results1 = calculator.process("2023-01-01 10:00:00", "2023-01-01 12:00:00")
        
        # Create a new calculator instance to test state loading
        calculator2 = IncrementalStdevCalculator(
            price_path=temp_data_files["data_path"],
            window_size=3,
            state_path=temp_data_files["state_path"]
        )
        
        calculator2.load_data()
        
        # Second processing run should load previous state
        results2 = calculator2.process("2023-01-01 13:00:00", "2023-01-01 15:00:00")
        
        # Both should succeed without errors
        assert isinstance(results1, pd.DataFrame)
        assert isinstance(results2, pd.DataFrame)

    def test_missing_data_handling(self, temp_data_files):
        """Test pipeline behavior with missing data points."""
        # Load original data and introduce gaps
        calculator = IncrementalStdevCalculator(
            price_path=temp_data_files["data_path"],
            window_size=5,
            state_path=temp_data_files["state_path"]
        )
        
        calculator.load_data()
        
        # Introduce NaN values in the data
        calculator.df.loc[calculator.df.index[::5], "mid"] = float('nan')
        
        # Process should handle NaN values gracefully
        results = calculator.process("2023-01-02 10:00:00", "2023-01-02 15:00:00")
        
        # Should not raise exceptions and should return a DataFrame
        assert isinstance(results, pd.DataFrame)

    def test_empty_time_range_processing(self, temp_data_files):
        """Test processing with time ranges that have no data."""
        calculator = IncrementalStdevCalculator(
            price_path=temp_data_files["data_path"],
            window_size=5,
            state_path=temp_data_files["state_path"]
        )
        
        calculator.load_data()
        
        # Process a time range outside the data range
        results = calculator.process("2025-01-01 10:00:00", "2025-01-01 15:00:00")
        
        # Should return empty DataFrame without errors
        assert isinstance(results, pd.DataFrame)
        assert len(results) == 0

    def test_large_window_size_handling(self, temp_data_files):
        """Test pipeline with window size larger than available data."""
        calculator = IncrementalStdevCalculator(
            price_path=temp_data_files["data_path"],
            window_size=1000,  # Much larger than available data
            state_path=temp_data_files["state_path"]
        )
        
        calculator.load_data()
        results = calculator.process("2023-01-02 10:00:00", "2023-01-02 15:00:00")
        
        # Should handle gracefully and return results (possibly with None values)
        assert isinstance(results, pd.DataFrame)

    def test_concurrent_processing_simulation(self, temp_data_files):
        """Test behavior that simulates concurrent processing scenarios."""
        # This tests the robustness of state management
        calculator1 = IncrementalStdevCalculator(
            price_path=temp_data_files["data_path"],
            window_size=5,
            state_path=temp_data_files["state_path"]
        )
        
        calculator2 = IncrementalStdevCalculator(
            price_path=temp_data_files["data_path"],
            window_size=5,
            state_path=temp_data_files["state_path"]
        )
        
        # Both calculators process different time ranges
        calculator1.load_data()
        calculator2.load_data()
        
        results1 = calculator1.process("2023-01-01 10:00:00", "2023-01-01 12:00:00")
        results2 = calculator2.process("2023-01-01 13:00:00", "2023-01-01 15:00:00")
        
        # Both should complete successfully
        assert isinstance(results1, pd.DataFrame)
        assert isinstance(results2, pd.DataFrame)

    def test_data_quality_validation(self, temp_data_files):
        """Test data quality validation throughout the pipeline."""
        calculator = IncrementalStdevCalculator(
            price_path=temp_data_files["data_path"],
            window_size=5,
            state_path=temp_data_files["state_path"]
        )
        
        calculator.load_data()
        
        # Validate data quality after loading
        assert calculator.df is not None
        assert len(calculator.df) > 0
        assert "timestamp" in calculator.df.columns
        assert "security_id" in calculator.df.columns
        assert all(col in calculator.df.columns for col in ["bid", "mid", "ask"])
        
        # Check data types
        assert calculator.df["timestamp"].dtype == "datetime64[ns]"
        assert calculator.df["security_id"].dtype == "object"
        
        # Process and validate results
        results = calculator.process("2023-01-02 10:00:00", "2023-01-02 15:00:00")
        
        if not results.empty:
            # Validate results data quality
            assert results["timestamp"].dtype == "datetime64[ns]"
            assert results["security_id"].dtype == "object"
            
            # Check for reasonable standard deviation values (should be >= 0)
            numeric_cols = ["bid_stdev", "mid_stdev", "ask_stdev"]
            for col in numeric_cols:
                if col in results.columns:
                    non_null_values = results[col].dropna()
                    if len(non_null_values) > 0:
                        msg = f"Negative values found in {col}"
                        assert all(non_null_values >= 0), msg


class TestDAGIntegration:
    """Test DAG loading and basic structure."""

    def test_dag_loading(self):
        """Test that DAGs can be loaded without import errors."""
        import platform
        
        dag_bag = DagBag(dag_folder="dags/", include_examples=False)
        
        # Check for import errors (this should always work)
        error_msg = f"DAG import errors: {dag_bag.import_errors}"
        assert len(dag_bag.import_errors) == 0, error_msg
        
        # On Windows, Airflow has known issues with DAG discovery
        # So we'll be more lenient and just ensure no import errors
        if platform.system() == "Windows":
            # On Windows, just ensure no import errors occurred
            # The DAG discovery might not work due to symlink issues
            print("Windows detected: Skipping DAG count check due to known "
                  "Airflow limitations")
        else:
            # On Linux/Mac, we expect full functionality
            assert len(dag_bag.dags) > 0, "No DAGs found"

    def test_dag_structure(self):
        """Test basic DAG structure and properties."""
        import platform
        
        dag_bag = DagBag(dag_folder="dags/", include_examples=False)
        
        # Skip this test on Windows due to Airflow limitations
        if platform.system() == "Windows":
            print("Windows detected: Skipping DAG structure test due to known "
                  "Airflow limitations")
            return
            
        for dag_id, dag in dag_bag.dags.items():
            # Basic DAG properties
            assert dag.dag_id is not None
            assert dag.description is not None or dag.doc_md is not None
            
            # Check that DAG has tasks
            assert len(dag.tasks) > 0, f"DAG {dag_id} has no tasks"
            
            # Check task dependencies are properly set
            for task in dag.tasks:
                assert task.dag_id == dag_id
                assert task.task_id is not None

    @patch.dict("os.environ", {"AIRFLOW_HOME": "/tmp/airflow_test"})
    def test_dag_validation_with_airflow_config(self):
        """Test DAG validation with Airflow configuration."""
        import platform

        # Skip this test on Windows due to Airflow limitations
        if platform.system() == "Windows":
            print("Windows detected: Skipping Airflow config test due to known "
                  "limitations")
            return
            
        dag_bag = DagBag(dag_folder="dags/", include_examples=False)
        
        # Should load without configuration errors
        assert len(dag_bag.import_errors) == 0
        
        # Test that tasks can be instantiated
        for dag_id, dag in dag_bag.dags.items():
            for task in dag.tasks:
                # Basic task validation
                assert hasattr(task, "execute")
                assert task.task_id is not None
