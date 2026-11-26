"""Run the shared FxTypeFormatter probe driver for this packet."""
from pathlib import Path
import runpy

HERE = Path(__file__).parent
SHARED = HERE.parent / "sqlite06_reverb_fxtype_deleting_destroy/check.py"

if __name__ == "__main__":
    runpy.run_path(str(SHARED))["main"](HERE.name)
