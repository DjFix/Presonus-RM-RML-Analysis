from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'real10_g08_s03'))
import check
check.main('real10_g08_s04')
