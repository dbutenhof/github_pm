"""Pytest configuration and fixtures."""

import sys
from pathlib import Path

# Add src directory to Python path for imports
backend_dir = Path(__file__).parent.parent
src_dir = backend_dir / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

