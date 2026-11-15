"""D0 shares the independently range-checked original ARM producer with D2."""
import importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('storm_native_shared',Path(__file__).resolve().parent.parent/'trial10x2_storm_d2/native.py')
shared=importlib.util.module_from_spec(spec);spec.loader.exec_module(shared)
generate=shared.generate
