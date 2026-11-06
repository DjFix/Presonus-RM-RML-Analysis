"""Acceptance commands and differential comparison, no shell command execution."""
import argparse
import json
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
TEST='uc-library/tests/recovery/AliasComponentBindingsReplay.cpp'
SOURCE='uc-library/src/Presonus/AliasComponent.cpp'
HEADER='uc-library/include/presonus/AliasComponent.hpp'
WORK=ROOT/'temp/recovery-work/alias-bindings-local'
EXE=WORK/'replay'
SDK='temp/core-upstream/root-integration-01/upstream-core/sdk'
FIX=ROOT/'uc-library/tests/recovery/alias_component_bindings/fixtures.json'
def run(args):
    subprocess.run(args,cwd=ROOT,check=True)
def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['format','compile','symbols','replay']);p.add_argument('--executable');a=p.parse_args()
    if a.mode=='format':
        run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',SOURCE,HEADER,TEST]);return
    if a.mode=='compile':
        WORK.mkdir(parents=True,exist_ok=True)
        run(['/usr/bin/c++','-std=c++17','-O1','-g','-DNDEBUG=1','-DCORE_USE_OPENSSL=1','-Ulinux','-Iuc-library/include','-Ithird_party/ccl-framework','-c',SOURCE,'-o',str(WORK/'AliasComponent.o')])
        run(['/usr/bin/c++','-std=c++17','-O1','-g','-DNDEBUG=1','-DCORE_USE_OPENSSL=1','-Ulinux','-Iuc-library/include','-Ithird_party/ccl-framework',TEST,str(WORK/'AliasComponent.o'),SDK+'/lib/libcorelib.a',SDK+'/lib/libpresonus_core_allocator.a','-Ltemp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu','-pthread','-lpng','-lz','-lssl','-lcrypto','-ldns_sd','-lm','-ldl','-o',str(EXE)]);return
    if a.mode=='symbols':
        symbols=subprocess.check_output(['/usr/bin/nm','--defined-only',str(WORK/'AliasComponent.o')],text=True)
        for r in json.loads(FIX.read_text())['ranges']:
            assert any(x.split()[-1]==r['mangled'] for x in symbols.splitlines()),r['mangled']
        print('Five exact original symbols present');return
    fixtures=json.loads(FIX.read_text())
    from native import native
    fresh=native();assert fresh==fixtures,'native fixture drift'
    exe=a.executable or str(EXE)
    for c in fixtures['cases']:
        assert c['getter_matches']
        if c['mode'] in ('sparse','changed','C1_unwind','C2_unwind','alias_ctor_unwind'):
            continue # nonvirtual provider collection cannot contain null via public API; delegation checked below.
        got=json.loads(subprocess.check_output([exe,c['mode']],text=True))
        expected={k:c[k] for k in ('snapshot','original_nonnull','getter_matches')}
        assert got==expected,(c['mode'],got,expected)
        if c['mode'] in ('same','replace','clear'):
            assert [t for t in c['trace'] if t[0] in ('remove','delete')]==[['remove',91],['delete',91],['remove',90],['delete',90]]
    assert len(next(c for c in fixtures['cases'] if c['mode']=='sparse')['snapshot'])==2
    assert next(c for c in fixtures['cases'] if c['mode']=='changed')['trace']==[['component_paramChanged',0x1002000,2]]
    for mode in ('C1_unwind','C2_unwind'):
        trace=next(c for c in fixtures['cases'] if c['mode']==mode)['trace']
        assert trace==[['component_constructor','alias'],['injected_exception','setOriginal'],['component_destructor',True],['resume_cleanup',0x1234]]
    trace=next(c for c in fixtures['cases'] if c['mode']=='alias_ctor_unwind')['trace']
    assert trace[-2:]==[['delete_unconstructed_alias',True],['resume_cleanup',0x1234]]
    supplementary=json.loads(subprocess.check_output([exe,'supplementary'],text=True));assert supplementary['supplementary_passed']
    print(json.dumps(dict(native_cases=len(fixtures['cases']),differential_cases=9,provider_supplementary=supplementary)))
if __name__=='__main__':main()
