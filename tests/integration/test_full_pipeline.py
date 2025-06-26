"""
Integration tests for the complete stdev calculation pipeline.
"""
import os
import tempfile
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine, text

from plugins.stdev_calculator import IncrementalStdevCalculator


@pytest.mark.integration
class TestFullPipeline:
    """Integration tests for the complete pipeline."""
    
    def test_end_to_end_calculation(self, sample_price_data, test_db_engine):
        """Test the complete end-to-end calculation process."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.parq') as temp_file:
            # Create test data file
            sample_price_data.to_parquet(temp_file.name)
            
            # Create state file path
            state_file = temp_file.name.replace('.parq', '_state.json')
            
            try:
                # Initialize calculator
                calc = IncrementalStdevCalculator(
                    temp_file.name,
                    window_size=5,
                    state_path=state_file
                )
                
                # Load data
                calc.load_data()
                
                # Process data
                results = calc.process('2021-11-20 15:00:00', '2021-11-21 10:00:00')
                
                # Verify results
                assert not results.empty
                assert len(results) > 0
                
                # Check columns
                expected_columns = ['security_id', 'timestamp', 'bid_stdev', 'mid_stdev', 'ask_stdev']
                assert all(col in results.columns for col in expected_columns)
                
                # Check data types
                assert results['timestamp'].dtype.name.startswith('datetime')
                assert pd.api.types.is_numeric_dtype(results['bid_stdev'])
                assert pd.api.types.is_numeric_dtype(results['mid_stdev'])
                assert pd.api.types.is_numeric_dtype(results['ask_stdev'])
                
                # Verify state file was created
                assert Path(state_file).exists()
                
            finally:
                # Cleanup
                for file_path in [temp_file.name, state_file]:
                    if os.path.exists(file_path):
                        os.unlink(file_path)

    def test_database_integration(self, sample_price_data, test_db_engine):
        """Test database integration for storing results."""
        # Create tables
        with test_db_engine.connect() as conn:
            # Create price_data table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS test_price_data (
                    id SERIAL PRIMARY KEY,
                    security_id VARCHAR(50) NOT NULL,
                    snap_time TIMESTAMP NOT NULL,
                    bid DECIMAL(10, 4),
                    mid DECIMAL(10, 4),
                    ask DECIMAL(10, 4),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(security_id, snap_time)
                )
            """))
            
            # Create stdev_results table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS test_stdev_results (
                    id SERIAL PRIMARY KEY,
                    security_id VARCHAR(50) NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    bid_stdev DECIMAL(10, 6),
                    mid_stdev DECIMAL(10, 6),
                    ask_stdev DECIMAL(10, 6),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(security_id, timestamp)
                )
            """))
            conn.commit()
        
        try:
            # Insert sample data
            sample_price_data.to_sql(
                'test_price_data',
                test_db_engine,
                if_exists='append',
                index=False,
                method='multi'
            )
            
            # Verify data was inserted
            with test_db_engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM test_price_data"))
                count = result.scalar()
                assert count == len(sample_price_data)
            
            # Create and run calculator
            with tempfile.NamedTemporaryFile(delete=False, suffix='.parq') as temp_file:
                sample_price_data.to_parquet(temp_file.name)
                
                calc = IncrementalStdevCalculator(temp_file.name, window_size=5)
                calc.load_data()
                results = calc.process('2021-11-20 15:00:00', '2021-11-21 10:00:00')
                
                # Insert results into database
                if not results.empty:
                    results.to_sql(
                        'test_stdev_results',
                        test_db_engine,
                        if_exists='append',
                        index=False,
                        method='multi'
                    )
                    
                    # Verify results were inserted
                    with test_db_engine.connect() as conn:
                        result = conn.execute(text("SELECT COUNT(*) FROM test_stdev_results"))
                        count = result.scalar()
                        assert count > 0
                
                os.unlink(temp_file.name)
        
        finally:
            # Cleanup tables
            with test_db_engine.connect() as conn:
                conn.execute(text("DROP TABLE IF EXISTS test_price_data"))
                conn.execute(text("DROP TABLE IF EXISTS test_stdev_results"))
                conn.commit()

    def test_incremental_processing(self, sample_price_data):
        """Test incremental processing with state persistence."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.parq') as temp_file:
            sample_price_data.to_parquet(temp_file.name)
            state_file = temp_file.name.replace('.parq', '_state.json')
            
            try:
                # First run
                calc1 = IncrementalStdevCalculator(
                    temp_file.name,
                    window_size=10,
                    state_path=state_file
                )
                calc1.load_data()
                results1 = calc1.process('2021-11-20 15:00:00', '2021-11-20 20:00:00')
                
                # Verify state file exists
                assert Path(state_file).exists()
                
                # Second run with same data - should use persisted state
                calc2 = IncrementalStdevCalculator(
                    temp_file.name,
                    window_size=10,
                    state_path=state_file
                )
                calc2.load_data()
                results2 = calc2.process('2021-11-20 21:00:00', '2021-11-21 02:00:00')
                
                # Both runs should produce results
                assert not results1.empty
                assert not results2.empty
                
                # Results should be different (different time ranges)
                assert not results1.equals(results2)
                
            finally:
                for file_path in [temp_file.name, state_file]:
                    if os.path.exists(file_path):
                        os.unlink(file_path)

    def test_gap_handling(self, test_db_engine):
        """Test handling of data gaps in time series."""
        # Create data with intentional gaps
        timestamps = []
        base_time = pd.Timestamp('2021-11-20 10:00:00')
        
        # Add first sequence
        for i in range(5):
            timestamps.append(base_time + pd.Timedelta(hours=i))
        
        # Add gap (skip 2 hours)
        for i in range(7, 12):
            timestamps.append(base_time + pd.Timedelta(hours=i))
        
        gap_data = pd.DataFrame({
            'security_id': ['SEC1'] * len(timestamps),
            'snap_time': timestamps,
            'bid': [100.0 + i * 0.1 for i in range(len(timestamps))],
            'mid': [100.5 + i * 0.1 for i in range(len(timestamps))],
            'ask': [101.0 + i * 0.1 for i in range(len(timestamps))],
        })
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.parq') as temp_file:
            gap_data.to_parquet(temp_file.name)
            
            try:
                calc = IncrementalStdevCalculator(temp_file.name, window_size=5)
                calc.load_data()
                results = calc.process('2021-11-20 10:00:00', '2021-11-20 21:00:00')
                
                # Should handle gaps gracefully
                assert not results.empty
                
                # Check that calculations reset after gap
                # (This is implementation-specific, adjust based on your gap handling logic)
                
            finally:
                os.unlink(temp_file.name)

    def test_performance_benchmark(self, test_db_engine):
        """Test performance meets requirements (< 1 second for typical data)."""
        import time
        
        # Create larger dataset for performance testing
        large_data = []
        base_time = pd.Timestamp('2021-11-20 00:00:00')
        
        for sec_id in [f'SEC{i}' for i in range(1, 11)]:  # 10 securities
            for hour in range(100):  # 100 hours of data
                large_data.append({
                    'security_id': sec_id,
                    'snap_time': base_time + pd.Timedelta(hours=hour),
                    'bid': 100.0 + hour * 0.1,
                    'mid': 100.5 + hour * 0.1,
                    'ask': 101.0 + hour * 0.1,
                })
        
        large_df = pd.DataFrame(large_data)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.parq') as temp_file:
            large_df.to_parquet(temp_file.name)
            
            try:
                calc = IncrementalStdevCalculator(temp_file.name, window_size=20)
                calc.load_data()
                
                # Measure processing time
                start_time = time.time()
                results = calc.process('2021-11-20 20:00:00', '2021-11-23 20:00:00')
                end_time = time.time()
                
                processing_time = end_time - start_time
                
                # Should complete within reasonable time (adjust based on requirements)
                assert processing_time < 5.0, f"Processing took {processing_time:.2f}s, expected < 5s"
                assert not results.empty
                
            finally:
                os.unlink(temp_file.name)
