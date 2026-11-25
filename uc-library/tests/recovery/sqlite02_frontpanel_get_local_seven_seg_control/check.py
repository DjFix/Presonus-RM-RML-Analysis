"""Run shared FrontPanel build and exact native/portable comparison."""
import importlib.util
from pathlib import Path

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location(
    "frontpanel_check", HERE.parent / "sqlite02_frontpanel_get_local_fader_style" /
    "check.py")
shared = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shared)

if __name__ == "__main__":
    shared.main(HERE)
