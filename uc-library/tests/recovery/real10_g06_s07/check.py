import importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('shared',Path(__file__).parent.parent/'real10_g06_s04/check.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
module.main(Path(__file__).parent.name)
