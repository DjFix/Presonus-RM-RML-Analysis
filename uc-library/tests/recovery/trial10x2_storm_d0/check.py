import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'trial10x2_storm_d2'))
from check import main
if __name__=='__main__':main('d0')
