"""Run the shared replay against the exact getObjectForView fixture."""

from pathlib import Path
import runpy
import sys

if __name__ == "__main__":
    common = Path(__file__).resolve().parent.parent / "sqlite02_scribblestripcontroller_create_view_r2/check.py"
    sys.path.insert(0, str(common.parent))
    runpy.run_path(str(common), run_name="__main__")
