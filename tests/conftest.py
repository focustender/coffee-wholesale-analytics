"""
Puts data/ and analysis/ on sys.path so tests can import their modules
directly (generate_dataset.py, reconcile_lifecycle.py), matching the same
sys.path.insert pattern the scripts themselves already use to reach across
directories -- no package structure to introduce for two test files.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
for sub in ("data", "analysis"):
    sys.path.insert(0, str(ROOT / sub))
