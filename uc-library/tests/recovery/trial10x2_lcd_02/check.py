# Both handoffs bind the final same-lane shared implementation and replay.
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().parents[1]/'trial10x2_lcd_01/check.py'),run_name='__main__')
