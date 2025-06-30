# Test configuration and utilities
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Test data directory
TEST_DATA_DIR = project_root / "tests" / "data"
TEST_DATA_DIR.mkdir(exist_ok=True)

# Common test utilities can be added here
