"""Run the shared, hash-bound RemoteEventSender ARM oracle for this packet."""
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.argv.extend(("--task", HERE.name))
runpy.run_path(str(HERE.parent / "sqlite02_remoteeventsender_complete_construct/native.py"),
               run_name="__main__")
