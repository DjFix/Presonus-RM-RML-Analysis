import importlib.util
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"rolling10_presets_01"/"check.py"
spec=importlib.util.spec_from_file_location("presets_check",p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
if __name__=="__main__":m.main("rolling10_presets_02")
