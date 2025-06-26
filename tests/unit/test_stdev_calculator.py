"""
Unit tests for the IncrementalStdevCalculator class.
"""
import json
import pandas as pd
import pytest
from collections import deque
from pathlib import Path

from plugins.stdev_calculator import IncrementalStdevCalculator


class TestIncrementalStdevCalculator:
    """Test class for IncrementalStdevCalculator."""
    
    def test_initialization(self, temp_parquet_file):
        """Test calculator initialization."""
        calc = IncrementalStdevCalculator(temp_parquet_file, window_size=10)
        
        assert calc.price_path == Path(temp_parquet_file)
        assert calc.window_size == 10
        assert calc.state_path is None
        assert calc.df is None
        assert calc.calculation_state == {}
    
    def test_initialization_with_state_path(self, temp_parquet_file, temp_state_file):
        """Test calculator initialization with state path."""
        calc = IncrementalStdevCalculator(
            temp_parquet_file, 
            window_size=15, 
            state_path=temp_state_file
        )
        
        assert calc.state_path == Path(temp_state_file)
        assert calc.window_size == 15

    def test_get_state_key(self, temp_parquet_file):
        """Test state key generation."""
        calc = IncrementalStdevCalculator(temp_parquet_file)
        
        key = calc._get_state_key('SEC1', 'bid')
        assert key == 'SEC1_bid'
        
        key = calc._get_state_key('ABC123', 'ask')
        assert key == 'ABC123_ask'

    def test_initialize_state(self, temp_parquet_file):
        """Test state initialization."""
        calc = IncrementalStdevCalculator(temp_parquet_file)
        calc.calculation_state = {'test': 'data'}
        
        calc._initialize_state()
        assert calc.calculation_state == {}

    def test_load_data_basic(self, temp_parquet_file, sample_price_data):
        """Test basic data loading."""
        calc = IncrementalStdevCalculator(temp_parquet_file)
        calc.load_data()
        
        assert calc.df is not None
        assert len(calc.df) == len(sample_price_data)
        assert 'timestamp' in calc.df.columns
        assert calc.df['timestamp'].dtype.name.startswith('datetime')

    def test_load_data_with_existing_state(self, temp_parquet_file, temp_state_file):
        """Test data loading with existing state file."""
        # Create a mock state file
        state_data = {
            'SEC1_bid': {
                'values': [100.0, 100.1, 100.2],
                'sum': 300.3,
                'sum_sq': 30030.05,
                'last_timestamp': '2021-11-20T10:00:00'
            }
        }
        
        with open(temp_state_file, 'w') as f:
            json.dump(state_data, f)
        
        calc = IncrementalStdevCalculator(temp_parquet_file, state_path=temp_state_file)
        calc.load_data()
        
        assert 'SEC1_bid' in calc.calculation_state
        state = calc.calculation_state['SEC1_bid']
        assert isinstance(state['values'], deque)
        assert list(state['values']) == [100.0, 100.1, 100.2]
        assert state['sum'] == 300.3
        assert state['sum_sq'] == 30030.05

    def test_load_data_with_corrupted_state(self, temp_parquet_file, temp_state_file):
        """Test data loading with corrupted state file."""
        # Create a corrupted state file
        with open(temp_state_file, 'w') as f:
            f.write('invalid json')
        
        calc = IncrementalStdevCalculator(temp_parquet_file, state_path=temp_state_file)
        calc.load_data()
        
        # Should initialize empty state on corruption
        assert calc.calculation_state == {}

    def test_update_state_first_value(self, temp_parquet_file):
        """Test state update with first value."""
        calc = IncrementalStdevCalculator(temp_parquet_file, window_size=3)
        calc.load_data()
        
        result = calc._update_state('SEC1_bid', 100.0, '2021-11-20 10:00:00')
        
        assert result is None  # Not enough values for stdev
        assert 'SEC1_bid' in calc.calculation_state
        state = calc.calculation_state['SEC1_bid']
        assert len(state['values']) == 1
        assert state['sum'] == 100.0
        assert state['sum_sq'] == 10000.0

    def test_update_state_full_window(self, temp_parquet_file):
        """Test state update with full window."""
        calc = IncrementalStdevCalculator(temp_parquet_file, window_size=3)
        calc.load_data()
        
        # Add values to fill window
        calc._update_state('SEC1_bid', 100.0, '2021-11-20 10:00:00')
        calc._update_state('SEC1_bid', 101.0, '2021-11-20 11:00:00')
        result = calc._update_state('SEC1_bid', 102.0, '2021-11-20 12:00:00')
        
        assert result is not None
        assert isinstance(result, float)
        assert result > 0  # Standard deviation should be positive

    def test_update_state_gap_detection(self, temp_parquet_file):
        """Test gap detection and state reset."""
        calc = IncrementalStdevCalculator(temp_parquet_file, window_size=3)
        calc.load_data()
        
        # Add initial values
        calc._update_state('SEC1_bid', 100.0, '2021-11-20 10:00:00')
        calc._update_state('SEC1_bid', 101.0, '2021-11-20 11:00:00')
        
        # Create a gap (skip 12:00:00)
        calc._update_state('SEC1_bid', 102.0, '2021-11-20 13:00:00')
        
        state = calc.calculation_state['SEC1_bid']
        # After gap, should only have the last value
        assert len(state['values']) == 1
        assert state['sum'] == 102.0

    def test_process_basic(self, temp_parquet_file):
        """Test basic processing."""
        calc = IncrementalStdevCalculator(temp_parquet_file, window_size=5)
        calc.load_data()
        
        result_df = calc.process('2021-11-20 15:00:00', '2021-11-20 20:00:00')
        
        assert isinstance(result_df, pd.DataFrame)
        assert not result_df.empty
        expected_columns = ['security_id', 'timestamp', 'bid_stdev', 'mid_stdev', 'ask_stdev']
        assert all(col in result_df.columns for col in expected_columns)

    def test_process_with_state_persistence(self, temp_parquet_file, temp_state_file):
        """Test processing with state persistence."""
        calc = IncrementalStdevCalculator(
            temp_parquet_file, 
            window_size=5, 
            state_path=temp_state_file
        )
        calc.load_data()
        
        result_df = calc.process('2021-11-20 15:00:00', '2021-11-20 20:00:00')
        
        # Check that state file was created
        assert Path(temp_state_file).exists()
        
        # Verify state file content
        with open(temp_state_file, 'r') as f:
            state_data = json.load(f)
        
        assert len(state_data) > 0
        # Should have states for multiple securities and price types
        assert any('SEC1' in key for key in state_data.keys())
        assert any('SEC2' in key for key in state_data.keys())

    def test_save_results(self, temp_parquet_file, temp_dir):
        """Test saving results to CSV."""
        calc = IncrementalStdevCalculator(temp_parquet_file)
        calc.load_data()
        
        result_df = calc.process('2021-11-20 15:00:00', '2021-11-20 20:00:00')
        output_path = temp_dir / 'test_results.csv'
        
        calc.save(result_df, output_path)
        
        assert output_path.exists()
        
        # Verify saved data
        saved_df = pd.read_csv(output_path)
        assert len(saved_df) == len(result_df)
        assert list(saved_df.columns) == list(result_df.columns)

    def test_rolling_stdev_accuracy(self, temp_parquet_file):
        """Test accuracy of rolling standard deviation calculation."""
        calc = IncrementalStdevCalculator(temp_parquet_file, window_size=5)
        calc.load_data()
        
        # Create test data with known standard deviation
        test_values = [100.0, 101.0, 102.0, 103.0, 104.0]
        key = 'TEST_bid'
        
        # Manually add values
        for i, value in enumerate(test_values):
            timestamp = f'2021-11-20 {10+i}:00:00'
            result = calc._update_state(key, value, timestamp)
        
        # Calculate expected standard deviation manually
        expected_stdev = pd.Series(test_values).std(ddof=1)
        
        assert result is not None
        assert abs(result - expected_stdev) < 1e-10  # High precision check

    @pytest.mark.parametrize("window_size", [5, 10, 20])
    def test_different_window_sizes(self, temp_parquet_file, window_size):
        """Test calculator with different window sizes."""
        calc = IncrementalStdevCalculator(temp_parquet_file, window_size=window_size)
        calc.load_data()
        
        result_df = calc.process('2021-11-20 15:00:00', '2021-11-20 20:00:00')
        
        assert isinstance(result_df, pd.DataFrame)
        # Results should be consistent regardless of window size
        assert not result_df.empty
