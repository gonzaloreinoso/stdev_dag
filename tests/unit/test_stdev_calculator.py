"""Unit tests for the IncrementalStdevCalculator class."""

import json
import tempfile
from collections import deque
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from plugins.stdev_calculator import IncrementalStdevCalculator


class TestIncrementalStdevCalculator:
    """Test suite for IncrementalStdevCalculator."""

    @pytest.fixture
    def sample_data(self):
        """Create sample price data for testing."""
        data = {
            "security_id": ["SEC1", "SEC1", "SEC1", "SEC2", "SEC2", "SEC2"],
            "snap_time": [
                "2023-01-01 10:00:00",
                "2023-01-01 11:00:00",
                "2023-01-01 12:00:00",
                "2023-01-01 10:00:00",
                "2023-01-01 11:00:00",
                "2023-01-01 12:00:00",
            ],
            "bid": [100.0, 101.0, 102.0, 200.0, 201.0, 202.0],
            "mid": [100.5, 101.5, 102.5, 200.5, 201.5, 202.5],
            "ask": [101.0, 102.0, 103.0, 201.0, 202.0, 203.0],
        }
        return pd.DataFrame(data)

    @pytest.fixture
    def temp_parquet_file(self, sample_data):
        """Create a temporary parquet file with sample data."""
        with tempfile.NamedTemporaryFile(suffix=".parq", delete=False) as f:
            sample_data.to_parquet(f.name)
            yield f.name
        Path(f.name).unlink(missing_ok=True)

    @pytest.fixture
    def temp_state_file(self):
        """Create a temporary state file path."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            yield f.name
        Path(f.name).unlink(missing_ok=True)

    @pytest.fixture
    def calculator(self, temp_parquet_file, temp_state_file):
        """Create a calculator instance for testing."""
        return IncrementalStdevCalculator(
            price_path=temp_parquet_file,
            window_size=3,
            state_path=temp_state_file
        )

    def test_init(self, temp_parquet_file, temp_state_file):
        """Test calculator initialization."""
        calc = IncrementalStdevCalculator(
            price_path=temp_parquet_file,
            window_size=5,
            state_path=temp_state_file
        )
        
        assert calc.price_path == Path(temp_parquet_file)
        assert calc.window_size == 5
        assert calc.state_path == Path(temp_state_file)
        assert calc.df is None
        assert calc.calculation_state == {}

    def test_init_without_state_path(self, temp_parquet_file):
        """Test calculator initialization without state path."""
        calc = IncrementalStdevCalculator(price_path=temp_parquet_file)
        
        assert calc.price_path == Path(temp_parquet_file)
        assert calc.window_size == 20  # default
        assert calc.state_path is None

    def test_get_state_key(self, calculator):
        """Test state key generation."""
        key = calculator._get_state_key("SEC1", "bid")
        assert key == "SEC1_bid"
        
        key = calculator._get_state_key("ABC123", "mid")
        assert key == "ABC123_mid"

    def test_initialize_state(self, calculator):
        """Test state initialization."""
        calculator.calculation_state = {"test": "data"}
        calculator._initialize_state()
        assert calculator.calculation_state == {}

    def test_load_data(self, calculator):
        """Test data loading from parquet file."""
        calculator.load_data()
        
        assert calculator.df is not None
        assert "timestamp" in calculator.df.columns
        assert "security_id" in calculator.df.columns
        assert len(calculator.df) > 0
        
        # Check if data is sorted
        for sec_id in calculator.df["security_id"].unique():
            sec_data = calculator.df[calculator.df["security_id"] == sec_id]
            timestamps = sec_data["timestamp"].values
            assert all(timestamps[i] <= timestamps[i+1] for i in range(len(timestamps)-1))

    def test_update_state_new_key(self, calculator):
        """Test updating state with a new key."""
        calculator.window_size = 3
        
        result = calculator._update_state("SEC1_bid", 100.0, "2023-01-01 10:00:00")
        
        assert "SEC1_bid" in calculator.calculation_state
        state = calculator.calculation_state["SEC1_bid"]
        assert len(state["values"]) == 1
        assert state["sum"] == 100.0
        assert state["sum_sq"] == 10000.0
        assert result is None  # Not enough values for stdev yet

    def test_update_state_full_window(self, calculator):
        """Test updating state when window is full."""
        calculator.window_size = 3
        
        # Add values to fill the window
        calculator._update_state("SEC1_bid", 100.0, "2023-01-01 10:00:00")
        calculator._update_state("SEC1_bid", 101.0, "2023-01-01 11:00:00")
        result = calculator._update_state("SEC1_bid", 102.0, "2023-01-01 12:00:00")
        
        assert result is not None
        assert isinstance(result, float)
        assert result > 0  # Standard deviation should be positive

    def test_update_state_with_nan(self, calculator):
        """Test updating state with NaN values."""
        calculator.window_size = 3
        
        # Add some values first
        calculator._update_state("SEC1_bid", 100.0, "2023-01-01 10:00:00")
        calculator._update_state("SEC1_bid", 101.0, "2023-01-01 11:00:00")
        
        # Add NaN value
        calculator._update_state("SEC1_bid", np.nan, "2023-01-01 12:00:00")
        
        state = calculator.calculation_state["SEC1_bid"]
        assert len(state["values"]) == 0  # Should be reset
        assert state["sum"] == 0.0
        assert state["sum_sq"] == 0.0

    def test_update_state_window_overflow(self, calculator):
        """Test updating state when window size is exceeded."""
        calculator.window_size = 2
        
        # Add more values than window size
        calculator._update_state("SEC1_bid", 100.0, "2023-01-01 10:00:00")
        calculator._update_state("SEC1_bid", 101.0, "2023-01-01 11:00:00")
        calculator._update_state("SEC1_bid", 102.0, "2023-01-01 12:00:00")
        
        state = calculator.calculation_state["SEC1_bid"]
        assert len(state["values"]) == 2  # Should maintain window size
        assert list(state["values"]) == [101.0, 102.0]  # Should contain latest values

    def test_process_basic(self, calculator):
        """Test basic processing functionality."""
        calculator.load_data()
        
        start_time = "2023-01-01 10:00:00"
        end_time = "2023-01-01 12:00:00"
        
        result_df = calculator.process(start_time, end_time)
        
        assert isinstance(result_df, pd.DataFrame)
        if not result_df.empty:
            expected_columns = ["security_id", "timestamp", "bid_stdev", "mid_stdev", "ask_stdev"]
            assert all(col in result_df.columns for col in expected_columns)

    def test_save_state(self, calculator, temp_state_file):
        """Test saving calculation state to file."""
        calculator.calculation_state = {
            "SEC1_bid": {
                "values": deque([100.0, 101.0], maxlen=3),
                "sum": 201.0,
                "sum_sq": 20201.0,
                "last_timestamp": pd.Timestamp("2023-01-01 12:00:00"),
                "last_stdev": 0.5
            }
        }
        
        # Save state by calling process (which saves state internally)
        calculator.load_data()
        calculator.process("2023-01-01 10:00:00", "2023-01-01 12:00:00")
        
        # Check if state file was created
        assert Path(temp_state_file).exists()

    def test_load_existing_state(self, calculator, temp_state_file):
        """Test loading existing calculation state."""
        # Create a state file
        state_data = {
            "SEC1_bid": {
                "values": [100.0, 101.0],
                "sum": 201.0,
                "sum_sq": 20201.0,
                "last_timestamp": "2023-01-01T12:00:00",
                "last_stdev": 0.5
            }
        }
        
        with open(temp_state_file, "w") as f:
            json.dump(state_data, f)
        
        calculator.load_data()
        
        assert "SEC1_bid" in calculator.calculation_state
        state = calculator.calculation_state["SEC1_bid"]
        assert list(state["values"]) == [100.0, 101.0]
        assert state["sum"] == 201.0
        assert state["sum_sq"] == 20201.0
        assert state["last_stdev"] == 0.5

    def test_save_results_to_csv(self, calculator, tmp_path):
        """Test saving results to CSV file."""
        result_df = pd.DataFrame({
            "security_id": ["SEC1", "SEC2"],
            "timestamp": [pd.Timestamp("2023-01-01 10:00:00"), pd.Timestamp("2023-01-01 10:00:00")],
            "bid_stdev": [0.5, 0.7],
            "mid_stdev": [0.6, 0.8],
            "ask_stdev": [0.7, 0.9]
        })
        
        output_path = tmp_path / "results.csv"
        calculator.save(result_df, str(output_path))
        
        assert output_path.exists()
        loaded_df = pd.read_csv(output_path)
        assert len(loaded_df) == 2
        assert "security_id" in loaded_df.columns

    def test_ensure_hourly_snapshots(self, calculator):
        """Test hourly snapshot generation."""
        # Create test data with missing hours
        data = pd.DataFrame({
            "security_id": ["SEC1", "SEC1"],
            "timestamp": [
                pd.Timestamp("2023-01-01 10:00:00"),
                pd.Timestamp("2023-01-01 12:00:00")  # Missing 11:00:00
            ],
            "bid": [100.0, 102.0],
            "mid": [100.5, 102.5],
            "ask": [101.0, 103.0]
        })
        
        calculator.df = data
        calculator._ensure_hourly_snapshots()
        
        # Should have filled in the missing hour
        assert len(calculator.df) > len(data)
        
        # Check if 11:00:00 was added
        timestamps = calculator.df[calculator.df["security_id"] == "SEC1"]["timestamp"].values
        expected_timestamp = pd.Timestamp("2023-01-01 11:00:00")
        assert expected_timestamp in timestamps

    def test_empty_dataframe_handling(self, calculator):
        """Test handling of empty dataframes."""
        calculator.df = pd.DataFrame()
        calculator._ensure_hourly_snapshots()
        # Should not raise an exception
        assert calculator.df.empty

    @patch('pandas.read_parquet')
    def test_load_data_file_not_found(self, mock_read_parquet, calculator):
        """Test handling when parquet file doesn't exist."""
        mock_read_parquet.side_effect = FileNotFoundError("File not found")
        
        with pytest.raises(FileNotFoundError):
            calculator.load_data()

    def test_corrupted_state_file_handling(self, calculator, temp_state_file):
        """Test handling of corrupted state files."""
        # Create a corrupted state file
        with open(temp_state_file, "w") as f:
            f.write("invalid json content")
        
        # Should not raise exception, should initialize empty state
        calculator.load_data()
        assert calculator.calculation_state == {}

    def test_stdev_calculation_accuracy(self, calculator):
        """Test standard deviation calculation accuracy."""
        calculator.window_size = 3
        
        # Test with known values
        values = [1.0, 2.0, 3.0]
        expected_stdev = np.std(values, ddof=1)  # Sample standard deviation
        
        for i, val in enumerate(values):
            result = calculator._update_state("test_key", val, f"2023-01-01 {10+i}:00:00")
        
        # Result should match numpy's calculation
        np.testing.assert_almost_equal(result, expected_stdev, decimal=10)
