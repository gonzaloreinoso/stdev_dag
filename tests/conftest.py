import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path
import tempfile

# Add parent directory to path to import modules
sys.path.append(str(Path(__file__).parent.parent))

@pytest.fixture
def test_data_path():
    """Create a temporary parquet file with test data."""
    with tempfile.NamedTemporaryFile(suffix=".parq.gzip", delete=False) as tmp:
        # Create a small dataset for testing
        dates = pd.date_range(start='2021-11-01', periods=100, freq='H')
        securities = ['SEC1', 'SEC2', 'SEC3']
        
        data = []
        for sec in securities:
            for ts in dates:
                # Create some predictable price data
                base_price = 100.0 if sec == 'SEC1' else 200.0 if sec == 'SEC2' else 300.0
                noise = np.random.normal(0, 1)
                bid = base_price - 0.5 + noise * 0.1
                ask = base_price + 0.5 + noise * 0.1
                mid = (bid + ask) / 2
                
                data.append({
                    'security_id': sec,
                    'snap_time': ts,
                    'bid': round(bid, 4),
                    'mid': round(mid, 4),
                    'ask': round(ask, 4)
                })
        
        df = pd.DataFrame(data)
        df.to_parquet(tmp.name, compression='gzip')
        
        yield tmp.name
        
        # Clean up
        try:
            Path(tmp.name).unlink()
        except:
            pass

@pytest.fixture
def state_file_path():
    """Provide a temporary path for the state file."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        yield tmp.name
        
        # Clean up
        try:
            Path(tmp.name).unlink()
        except:
            pass

@pytest.fixture
def results_path():
    """Provide a temporary path for output results."""
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        yield tmp.name
        
        # Clean up
        try:
            Path(tmp.name).unlink()
        except:
            pass
