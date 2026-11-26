"""Bounded launcher for genuine retained local bodies, without oracle edits."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import types

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


parser = argparse.ArgumentParser()
parser.add_argument('--profile', choices=('lpc', 'updater'), required=True)
parser.add_argument('--checker', type=Path, required=True)
parser.add_argument('--checker-sha256', required=True)
parser.add_argument('--exe', type=Path, required=True)
parser.add_argument('--library', type=Path)
parser.add_argument('--fixture', type=Path)
parser.add_argument('original_arguments', nargs=argparse.REMAINDER)
args = parser.parse_args()
checker = args.checker.resolve(strict=True)
exe = args.exe.resolve(strict=True)
assert sha(checker) == args.checker_sha256
assert (args.profile == 'lpc') == (args.fixture is not None)
assert (args.profile == 'updater') == (args.library is not None)
binary = args.library.resolve(strict=True) if args.library else exe
environment = load('current104_static_environment', HERE / 'local_symbol_environment.py')
names = environment.LPC if args.profile == 'lpc' else environment.UPDATER
st = binary.stat()
tag = hashlib.sha256(json.dumps({
    'binary': str(binary), 'sha256': sha(binary),
    'stat': [st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns],
    'mapper': sha(HERE / 'prepare_local_symbol_map.py'),
}, sort_keys=True).encode()).hexdigest()
directory = ROOT / 'temp/test-work/current104-static' / (args.profile + '-' + tag)
directory.mkdir(parents=True, exist_ok=True)
mapping = directory / 'MAP.json'
if not mapping.exists():
    command = [sys.executable, str(HERE / 'prepare_local_symbol_map.py'),
               str(binary), str(mapping)]
    for name in names:
        command += ['--symbol', name]
    subprocess.run(command, check=True, capture_output=True, text=True)
verified = environment.verified_environment(binary, mapping, args.profile)
binary_hashes = {str(p): sha(p) for p in {binary, exe}}
saved_environment = dict(os.environ)
for name in list(os.environ):
    if name.startswith('PRESONUS_'):
        del os.environ[name]
os.environ.update(verified)
original_run = subprocess.run
observations = []


def verify_inputs():
    assert environment.verified_environment(binary, mapping, args.profile) == verified
    assert {str(p): sha(p) for p in {binary, exe}} == binary_hashes
    assert sha(checker) == args.checker_sha256
    assert {k: v for k, v in os.environ.items() if k.startswith('PRESONUS_')} == verified


def checked_run(command, *positional, **keywords):
    assert Path(command[0]).resolve(strict=True) == exe, command
    verify_inputs()
    supplied = keywords.get('env', os.environ)
    assert {k: v for k, v in supplied.items() if k.startswith('PRESONUS_')} == verified
    started = time.monotonic()
    result = original_run(command, *positional, **keywords)
    verify_inputs()
    observations.append({'argv': list(map(str, command)), 'returncode': result.returncode,
                         'seconds': time.monotonic() - started})
    return result


try:
    module = load('unchanged_current104_original_checker', checker)
    module.subprocess = types.SimpleNamespace(run=checked_run)
    verify_inputs()
    if args.profile == 'lpc':
        assert not args.original_arguments
        module.replay(args.fixture.resolve(strict=True), exe)
    else:
        original = args.original_arguments
        assert original and original[0] == '--'
        original = original[1:]
        assert original[original.index('--exe') + 1] == str(exe)
        assert Path(original[original.index('--library') + 1]).resolve(strict=True) == binary
        assert original[original.index('--mode') + 1] == 'replay'
        sys.argv = [str(checker), *original]
        module.main()
    verify_inputs()
    receipt = {'passed': True, 'checker': str(checker), 'checker_sha256': sha(checker),
               'binary_hashes': binary_hashes, 'map': str(mapping), 'map_sha256': sha(mapping),
               'runtime_helper_sha256': sha(HERE / 'LocalSymbolRuntime104.hpp'),
               'mapper_sha256': sha(HERE / 'prepare_local_symbol_map.py'),
               'environment_helper_sha256': sha(HERE / 'local_symbol_environment.py'),
               'inherited_PRESONUS_variables_used': False,
               'before_and_after_each_subprocess_verified': True,
               'replays': observations, 'fixture_or_oracle_changes': False}
    output = directory / ('PASS-' + str(time.time_ns()) + '.json')
    output.write_text(json.dumps(receipt, indent=2) + '\n')
finally:
    os.environ.clear()
    os.environ.update(saved_environment)
