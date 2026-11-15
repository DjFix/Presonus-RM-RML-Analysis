"""Shared oracle producer; C2 range remains separately verified."""
import importlib.util
from pathlib import Path
P=Path(__file__).resolve().parent.parent/'trial10x2_groupobserver_01/native.py'
s=importlib.util.spec_from_file_location('groupobserver_shared_native',P)
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
generate=m.generate
ROOT=m.ROOT
B=m.B
READ=m.READ
ELF_SHA=m.ELF_SHA
