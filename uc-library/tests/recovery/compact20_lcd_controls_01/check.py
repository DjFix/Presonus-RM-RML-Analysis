"""Exact pointer-store replay and fresh proof producer; no readiness admission."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[4]
TEST = Path('uc-library/tests/recovery/compact20_lcd_controls_01')
SOURCES = [Path('uc-library/include/presonus/panel/MixerLCD.hpp'), Path('uc-library/src/Presonus/Panel/MixerLCD.cpp'), TEST / 'Replay.cpp']
MANGLED = '_ZN8Presonus5Panel8MixerLCD14setAltKeyParamEPN4Core8Portable9ParameterE'
DOMAIN = 'Borrowed pointer storage only:134 original ARM null/arbitrary32-bit pointer cases; corresponding actual CCL NumericParam/null pointer identity and replacement replay. No dereference, provider call, ownership transfer, original return declaration/layout/ARM ABI or hardware claim.'
def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def run(argv, **kwargs):
    r = subprocess.run(argv, check=True, text=True, capture_output=True, **kwargs)
    return {'argv': [str(x) for x in argv], 'returncode': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr}
def main():
    p = argparse.ArgumentParser()
    p.add_argument('mode', choices=['compile', 'symbols', 'replay'])
    p.add_argument('--out', required=True)
    p.add_argument('--executable')
    p.add_argument('--fixture', default=str(TEST / 'fixtures.json'))
    p.add_argument('--proof')
    p.add_argument('--integration-proof')
    p.add_argument('--object')
    args = p.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    binary = Path(args.executable) if args.executable else out / 'Replay'
    obj = Path(args.object) if args.object else out / 'MixerLCD.o'
    flags = ['c++', '-std=c++17', '-DCORE_PLATFORM_LINUX=1', '-Iuc-library/include', '-Ithird_party/ccl-framework']
    if args.mode == 'compile':
        commands = [run(flags + ['-c', str(SOURCES[1]), '-o', str(obj)])]
        commands.append(run(flags + [str(obj), str(TEST / 'Replay.cpp'), '-Wl,--start-group', 'temp/provider-baseline08/libcorelib.a', 'temp/provider-baseline08/libpresonus_core_allocator.a', '-Wl,--end-group', '-lpthread', '-ldl', '-l:libpng16.so.16', '-lz', '-o', str(binary)]))
        (out / 'compile.json').write_text(json.dumps({'commands': commands, 'object_sha256': digest(obj), 'executable_sha256': digest(binary)}, indent=2) + '\n')
        print('compiled')
    elif args.mode == 'symbols':
        result = run(['nm', '--defined-only', str(binary)])
        assert MANGLED in {line.split()[-1] for line in result['stdout'].splitlines() if line.split()}
        (out / 'symbols.json').write_text(json.dumps({'command': result, 'mangled': MANGLED, 'matched': True, 'executable_sha256': digest(binary)}, indent=2) + '\n')
        print(MANGLED)
    else:
        fixture = Path(args.fixture); f = json.loads(fixture.read_text()); assert f['cases'] == len(f['observations']) == 134
        assert digest(f['producer']['path']) == f['producer']['sha256']
        expected_trace = list(range(395712, 395732, 4))
        lines = []
        for row in f['observations']:
            assert int.from_bytes(bytes.fromhex(row['observed_stored_bytes']), 'little') == row['input_r1']
            assert row['trace'] == expected_trace and row['stack_restored'] and row['surrounding_memory_unchanged']
            assert len(row['object_writes']) == 1 and row['object_writes'][0] == {'address': 0x300110, 'size': 4, 'value': row['input_r1']}
            lines.append(str(row['case']) + ' ' + str(row['portable_case']))
        # Reuse independently observed native null-store case for clearing and repeated clearing.
        lines += [str(len(lines)) + ' 0', str(len(lines) + 1) + ' 0']
        result = run([str(binary.resolve())], input='\n'.join(lines) + '\n')
        assert result['stdout'].splitlines() == [line + ' 1' for line in lines]
        symbols = run(['nm', '--defined-only', str(binary)])
        assert MANGLED in {line.split()[-1] for line in symbols['stdout'].splitlines() if line.split()}
        fmt = '/home/rs/projects/opencs/ai-line-analysis/uc-library/.venv/bin/clang-format'
        format_check = run([fmt, '--style=file', '--fallback-style=LLVM', '--dry-run', '--Werror'] + [str(x) for x in SOURCES])
        proof = {'version': 1, 'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'cpp_differential_passed': True, 'compiled_mangled_names_matched': True, 'mangling_namespace_checked': True, 'functions': [{'original_elf_sha256': f['original']['original_elf_sha256'], 'mangled': MANGLED, 'domain': DOMAIN, 'native_cases': f['cases'], 'portable_cases':len(lines), 'cpp_compiled': True, 'portable_ready': False, 'declaration_uncertainties': ['Original return type is unencoded; void is a provisional portable declaration.']}], 'domain': DOMAIN, 'native_fixture': {'path': str(fixture), 'sha256': digest(fixture), 'producer': f['producer'], 'original': f['original'], 'original_file_offset': f['original_file_offset'], 'original_bytes_sha256': f['original_bytes_sha256'], 'unicorn_version': f['unicorn_version']}, 'source_hashes': {str(x): digest(x) for x in SOURCES}, 'producer_hashes': {str(TEST / name): digest(TEST / name) for name in ['native.py', 'check.py']}, 'repository_sources': {name: digest(name) for name in ['third_party/ccl-framework/core/portable/coreparams.h','third_party/ccl-framework/core/portable/coreparams.cpp','third_party/ccl-framework/core/portable/coreparaminfo.h']}, 'executable': {'path': str(binary), 'sha256': digest(binary)}, 'extra_portable_cases': {'count': 2, 'native_case_reused': 0, 'purpose': 'Clear previously stored nonnull pointer then repeat null store.'}, 'replay': result, 'symbols': {'argv': symbols['argv'], 'matched': MANGLED}, 'format': {'check': format_check, 'version': run([fmt, '--version'])['stdout']}, 'integration_proof': None, 'limitations': ['Only ARM app setter instructions executed, no Core binary execution.', 'Host pointers are actual CCL NumericParam addresses/null; arbitrary native pointer bits are not cast into host objects.', 'Pointer identity/storage semantics compared; native offsets and pointer width are not host ABI/layout claims.', 'No global integration or readiness admission claimed.']}
        if obj.exists(): proof['object'] = {'path': str(obj), 'sha256': digest(obj)}
        if args.integration_proof: proof['integration_proof'] = {'path': args.integration_proof, 'sha256': digest(args.integration_proof)}
        if args.proof:
            target = Path(args.proof)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('x') as stream:
                stream.write(json.dumps(proof, indent=2) + '\n')
        print(json.dumps({'native_cases': f['cases'], 'portable_cases': len(lines), 'matched': True}))
if __name__ == '__main__': main()
