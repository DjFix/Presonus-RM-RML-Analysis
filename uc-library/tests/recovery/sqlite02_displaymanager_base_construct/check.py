"""Run the shared DisplayManager comparison for the base constructor."""

import sys
from pathlib import Path

here = Path(__file__).parent
sys.path.insert(0, str(here.parent / "sqlite02_displaymanager_complete_construct"))

from check import replay

if __name__ == "__main__":
    replay(here)
