"""Add harness/ to sys.path so all test files can import the modules directly."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
