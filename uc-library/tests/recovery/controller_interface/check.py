"""Non-mutating checks except owned scratch build outputs."""
import hashlib, json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
BASE = Path('uc-library/tests/recovery/controller_interface')
OUT = Path('temp/recovery-work/controller173-local')
SOURCES = ['uc-library/src/Presonus/Dsp/Controller.cpp', 'uc-library/src/Presonus/Dsp/ControllerInfo.cpp', 'uc-library/src/Presonus/Dsp/ControllerSetupProcess.cpp', 'uc-library/src/Presonus/Dsp/ControllerInterface.cpp', 'uc-library/src/Presonus/Dsp/ParamDescriptorList.cpp', 'uc-library/tests/recovery/ControllerInterfaceReplay.cpp']
FORMAT = ['uc-library/include/presonus/dsp/IController.hpp', 'uc-library/include/presonus/dsp/Controller.hpp', 'uc-library/src/Presonus/Dsp/ControllerInterface.cpp', 'uc-library/tests/recovery/ControllerInterfaceReplay.cpp']
def run(argv, **kw):
    print(json.dumps(argv), flush=True)
    return subprocess.run(argv, cwd=ROOT, check=True, **kw)
def main():
    mode = sys.argv[1]
    OUT.mkdir(parents=True, exist_ok=True)
    if mode == 'format':
        run(['uc-library/.venv/bin/clang-format', '--version'])
        run(['uc-library/.venv/bin/clang-format', '--style=file', '--fallback-style=LLVM', '--dry-run', '--Werror'] + FORMAT)
    elif mode == 'compile':
        sdk = 'temp/core-upstream/root-integration-01/upstream-core/sdk'
        run(['g++', '-std=c++20', '-O0', '-g', '-Wall', '-Wextra', '-Iuc-library/include', '-Ithird_party/ccl-framework', '-I'+sdk+'/include/presonus-core-5'] + SOURCES + [sdk+'/lib/libcorelib.a', sdk+'/lib/libpresonus_core_allocator.a', 'temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a', '-pthread', '-ldl', '-o', str(OUT/'replay')])
    elif mode == 'symbols':
        symbols = run(['nm', '--defined-only', str(OUT/'replay')], capture_output=True, text=True).stdout
        for name in ('_ZN8Presonus3Dsp10Controller11getPropertyERN4Core8PropertyE', '_ZN8Presonus3Dsp10Controller11processIdleEv', '_ZNK8Presonus3Dsp10Controller13getNormalizedEi', '_ZN8Presonus3Dsp10Controller13setNormalizedEif', '_ZN8Presonus3Dsp10Controller11setPropertyERKN4Core8PropertyE', '_ZN8Presonus3Dsp10Controller7releaseEv'):
            assert any(line.split()[-1] == name for line in symbols.splitlines()), name
        (OUT/'symbols.txt').write_text(symbols)
        print('Exact original target and preserved method symbols passed')
    elif mode == 'replay':
        fixture = Path(sys.argv[2]) if len(sys.argv)>2 else BASE/'fixtures.json'
        data = json.loads(fixture.read_text())
        assert len(data['ranges']) == 2
        assert all(o['unchanged'] and not o['application_writes'] and not o['external_calls'] for r in data['ranges'] for o in r['observations'])
        executable = sys.argv[3] if len(sys.argv)>3 else str(OUT/'replay')
        inputs = ''.join(' '.join(str(c[k]) for k in ('type','size','iid','mode','seed'))+'\n' for c in data['cases'])
        result = run([executable], input=inputs, capture_output=True, text=True)
        print(result.stdout)
    elif mode == 'native':
        from native import generate
        assert generate() == json.loads((BASE/'fixtures.json').read_text())
        print('Independent original ARM replay matches sealed fixtures')
    else:
        raise ValueError(mode)
if __name__ == '__main__':
    main()
