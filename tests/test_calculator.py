import pytest
import pandas as pd
import numpy as np
import json
import sys
from pathlib import Path
from plugins.stdev_calculator import IncrementalStdevCalculator

class TestIncrementalStdevCalculator:
    """Test suite for the IncrementalStdevCalculator class."""
    
    def test_initialization(self, test_data_path, state_file_path):
        """Test that calculator initializes correctly with right parameters."""
        calculator = IncrementalStdevCalculator(
            price_path=test_data_path,
            window_size=10,  # Smaller window for easier testing
            state_path=state_file_path
        )
        
        assert calculator.price_path == Path(test_data_path)
        assert calculator.window_size == 10
        assert calculator.state_path == Path(state_file_path)
        assert calculator.df is None
        assert calculator.calculation_state == {}
    
    def test_load_data(self, test_data_path, state_file_path):
        """Test loading data from parquet file."""
        calculator = IncrementalStdevCalculator(
            price_path=test_data_path,
            window_size=10,
            state_path=state_file_path
        )
        
        calculator.load_data()
        
        # Verify data loaded correctly
        assert calculator.df is not None
        assert 'security_id' in calculator.df.columns
        assert 'timestamp' in calculator.df.columns
        assert 'bid' in calculator.df.columns
        assert 'mid' in calculator.df.columns
        assert 'ask' in calculator.df.columns
        
        # Verify state initialized
        assert isinstance(calculator.calculation_state, dict)
    
    def test_get_state_key(self, test_data_path):
        """Test state key generation."""
        calculator = IncrementalStdevCalculator(price_path=test_data_path)
        
        key = calculator._get_state_key('SEC1', 'bid')
        assert key == 'SEC1_bid'
        
        key = calculator._get_state_key('SEC2', 'ask')
        assert key == 'SEC2_ask'
    
    def test_update_state(self, test_data_path):
        """Test state updates and standard deviation calculation."""
        calculator = IncrementalStdevCalculator(price_path=test_data_path, window_size=5)
        
        # First update - should initialize state
        key = 'TEST_bid'
        ts = pd.Timestamp('2021-11-01 00:00:00')
        sd = calculator._update_state(key, 100.0, ts)
        
        # First value, should not have std dev yet
        assert sd is None
        assert key in calculator.calculation_state
        assert calculator.calculation_state[key]['sum'] == 100.0
        assert calculator.calculation_state[key]['sum_sq'] == 10000.0
        
        # Add more values
        sd = calculator._update_state(key, 101.0, ts + pd.Timedelta(hours=1))
        assert sd is None
        
        sd = calculator._update_state(key, 102.0, ts + pd.Timedelta(hours=2))
        assert sd is None
        
        sd = calculator._update_state(key, 103.0, ts + pd.Timedelta(hours=3))
        assert sd is None
        
        # Fifth value should trigger sd calculation
        sd = calculator._update_state(key, 104.0, ts + pd.Timedelta(hours=4))
        
        # Check the standard deviation result
        # For values [100, 101, 102, 103, 104], std ≈ 1.58
        assert sd is not None
        assert 1.57 < sd < 1.59
        
    def test_gap_detection(self, test_data_path):
        """Test that gaps in the data reset the state."""
        calculator = IncrementalStdevCalculator(price_path=test_data_path, window_size=3)
        
        key = 'TEST_bid'
        ts = pd.Timestamp('2021-11-01 00:00:00')
        
        # First sequence
        calculator._update_state(key, 100.0, ts)
        calculator._update_state(key, 101.0, ts + pd.Timedelta(hours=1))
        sd1 = calculator._update_state(key, 102.0, ts + pd.Timedelta(hours=2))
        
        # Gap in data (3 hours instead of 1)
        sd2 = calculator._update_state(key, 105.0, ts + pd.Timedelta(hours=5))
        
        # State should be reset, sd2 should be None
        assert sd2 is None
        assert len(calculator.calculation_state[key]['values']) == 1
        assert calculator.calculation_state[key]['sum'] == 105.0
    
    def test_process_method(self, test_data_path, state_file_path):
        """Test the main processing method."""
        calculator = IncrementalStdevCalculator(
            price_path=test_data_path,
            window_size=10,
            state_path=state_file_path
        )
        
        calculator.load_data()
        
        # Process a time range
        start_time = '2021-11-01 10:00:00'
        end_time = '2021-11-02 10:00:00'
        result_df = calculator.process(start_time, end_time)
        
        # Check results
        assert isinstance(result_df, pd.DataFrame)
        assert 'security_id' in result_df.columns
        assert 'timestamp' in result_df.columns
        assert 'bid_stdev' in result_df.columns
        assert 'mid_stdev' in result_df.columns
        assert 'ask_stdev' in result_df.columns
        
        # After window_size data points, we should have std dev values
        # Filter for timestamps after window_size hours from start
        window_cutoff = pd.Timestamp(start_time) + pd.Timedelta(hours=calculator.window_size)
        later_results = result_df[result_df['timestamp'] >= window_cutoff]
        
        if not later_results.empty:
            # Some results after window_size should have std devs
            assert not later_results['bid_stdev'].isna().all()
            assert not later_results['mid_stdev'].isna().all()
            assert not later_results['ask_stdev'].isna().all()
    
    def test_state_persistence(self, test_data_path, state_file_path):
        """Test that state is saved and loaded correctly."""
        # First calculator instance - calculate and save state
        calculator1 = IncrementalStdevCalculator(
            price_path=test_data_path,
            window_size=10,
            state_path=state_file_path
        )
        
        calculator1.load_data()
        calculator1.process('2021-11-01 00:00:00', '2021-11-01 12:00:00')
        
        # Verify the state file exists
        assert Path(state_file_path).exists()
        
        # Create a new calculator instance and load the saved state
        calculator2 = IncrementalStdevCalculator(
            price_path=test_data_path,
            window_size=10,
            state_path=state_file_path
        )
        
        calculator2.load_data()
        
        # Verify state was loaded
        assert calculator2.calculation_state != {}
        
        # Check structure of loaded state
        for key, state in calculator2.calculation_state.items():
            assert 'values' in state
            assert 'sum' in state
            assert 'sum_sq' in state
            assert 'last_timestamp' in state
    
    def test_save_results(self, test_data_path, results_path):
        """Test saving results to CSV file."""
        calculator = IncrementalStdevCalculator(price_path=test_data_path)
        
        # Create a sample results DataFrame
        data = {
            'security_id': ['SEC1', 'SEC1', 'SEC2'],
            'timestamp': pd.date_range(start='2021-11-01', periods=3),
            'bid_stdev': [0.1, 0.2, 0.3],
            'mid_stdev': [0.15, 0.25, 0.35],
            'ask_stdev': [0.2, 0.3, 0.4]
        }
        result_df = pd.DataFrame(data)
        
        # Save results
        calculator.save(result_df, results_path)
        
        # Verify file exists
        assert Path(results_path).exists()
        
        # Read back the file and verify contents
        df = pd.read_csv(results_path)
        assert len(df) == 3
        assert 'security_id' in df.columns
        assert 'timestamp' in df.columns
        assert 'bid_stdev' in df.columns
        assert list(df['bid_stdev']) == [0.1, 0.2, 0.3]
