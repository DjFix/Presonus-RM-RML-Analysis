"""C2 exact packet validation using the final shared class source bytes."""
import importlib.util
from pathlib import Path
P=Path(__file__).resolve().parent.parent/'trial10x2_groupobserver_01/check.py'
s=importlib.util.spec_from_file_location('groupobserver_shared_check',P)
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
if __name__=='__main__':m.main('trial10x2_groupobserver_02','C2',Path(__file__).resolve().parent)
