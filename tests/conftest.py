"""pytest conftest: ensure project root is on sys.path for imports"""

import os
import sys

# Add project root to sys.path so `from scripts.runner.utils import ...` works
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
