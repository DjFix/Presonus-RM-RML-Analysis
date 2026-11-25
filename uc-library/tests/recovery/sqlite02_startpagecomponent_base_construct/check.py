"""Apply the shared StartPage checks to the exact C2 packet."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

directory = Path(__file__).parent
shared = directory.with_name('sqlite02_startpagecomponent_complete_construct')
sys.path.insert(0, str(shared))
spec = spec_from_file_location('start_page_check', shared / 'check.py')
module = module_from_spec(spec)
spec.loader.exec_module(module)
module.main('C2', directory)
