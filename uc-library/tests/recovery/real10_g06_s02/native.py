import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).parent.parent/'real10_g06_s01/native.py'),run_name='__main__')
