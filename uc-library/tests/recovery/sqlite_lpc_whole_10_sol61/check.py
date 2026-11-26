"""Exact packet entry point; one class owner shares the replay implementation."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent.parent/"sqlite_lpc_whole_01_sol61"))
from check import main
if __name__=="__main__":main("sqlite_lpc_whole_10_sol61")
