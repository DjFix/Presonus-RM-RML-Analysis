"""Replay this exact task through the common scoped owner checker."""
import runpy,sys
from pathlib import Path
sys.argv.extend(["--task","sqlite_grfive_70e55547f68d"])
runpy.run_path(str(Path(__file__).parent.parent/"sqlite_grfive_24f6e99aab28"/"check.py"),run_name="__main__")
