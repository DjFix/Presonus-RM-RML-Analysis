#!/usr/bin/env python3
"""Standalone bounded build; writes only owned project scratch."""
import os
from pathlib import Path
import subprocess
p = Path('temp/recovery-work/graph-live-trial-08/mixerbase-worker')
p.mkdir(parents=True, exist_ok=True)
env = dict(os.environ, TMPDIR=str(p.resolve()))
argv = ['c++', '-std=c++17', '-Wall', '-Wextra', '-Werror', '-Iuc-library/include', 'uc-library/src/Presonus/Mixer/MixerComponentBase.cpp', 'uc-library/tests/graph_trial08_mixerbase_tests.cpp', '-o', str(p/'replay')]
print(argv, flush=True)
subprocess.run(argv, check=True, env=env)
