"""Exact packet native entry point; no hardware effects."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent.parent/"sqlite_lpc_whole_01_sol61"))
from native import generate
if __name__=="__main__":generate(sys.argv[1],"sqlite_lpc_whole_11_sol61")
