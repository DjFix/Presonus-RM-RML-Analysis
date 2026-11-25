"""Run the shared verified ConnectionHandler ARM oracle for this exact task."""
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.argv.extend(("--task", HERE.name))
runpy.run_path(str(HERE.parent / "sqlite02_connectionhandler_delete_all/native.py"),
               run_name="__main__")
