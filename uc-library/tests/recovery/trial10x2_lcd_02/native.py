# Same-lane shared independent oracle; both exact ranges are separately checked.
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().parents[1]/'trial10x2_lcd_01/native.py'),run_name='__main__')
