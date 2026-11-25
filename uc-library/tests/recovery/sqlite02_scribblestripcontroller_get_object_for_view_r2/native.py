"""Reuse the same bounded native executor for the other exact ELF symbol."""

import importlib.util
from pathlib import Path
import sys

module_path = Path(__file__).resolve().parent.parent / "sqlite02_scribblestripcontroller_create_view_r2/native.py"
spec = importlib.util.spec_from_file_location("scribble_native_common", module_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
observe = module.observe

if __name__ == "__main__":
    import json
    print(json.dumps(observe(Path(sys.argv[1]), sys.argv[2]), indent=2))
