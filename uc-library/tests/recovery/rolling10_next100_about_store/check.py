#!/usr/bin/env python3
"""Canonical executable replay and exact original range/provider validation."""
import argparse,datetime,hashlib,json,os,subprocess,sys
from pathlib import Path
import native
ROOT=Path(__file__).resolve().parents[4]
TASK=native.TASK
TEST=Path('uc-library/tests/recovery')/TASK
SCRATCH=Path('temp/recovery-work')/TASK
SRC=['uc-library/include/presonus/panel/SystemAboutPage.hpp','uc-library/src/Presonus/Panel/SystemAboutPage.cpp',str(TEST/'Replay.cpp')]
FLAGS=['-std=c++17','-O2','-fno-lto','-UNDEBUG','-Ulinux','-DCORE_USE_OPENSSL=1','-DPRESONUS_HAS_UPSTREAM_CORE=1','-Iuc-library/include','-Ithird_party/ccl-framework']
SDK=Path('/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/sdk/lib')
LIBS=[SDK/'libcorelib.a',SDK/'libpresonus_core_allocator.a']
MANGLED='_ZN8Presonus5Panel15SystemAboutPage5storeEv'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(argv,log=False):
    argv=list(map(str,argv))
    result=subprocess.run(argv,cwd=ROOT,env={**os.environ,'TMPDIR':str(ROOT/SCRATCH)},text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=True)
    if log:print(' '.join(argv)+'\n'+result.stdout,flush=True)
    return result.stdout
def main():
    p=argparse.ArgumentParser();p.add_argument('kind',nargs='?',choices=['format','compile','symbols','replay'],default='replay')
    p.add_argument('--exe',type=Path);p.add_argument('--object',type=Path);p.add_argument('--integration',type=Path);p.add_argument('--out',type=Path)
    a=p.parse_args();os.chdir(ROOT);(ROOT/SCRATCH).mkdir(parents=True,exist_ok=True)
    obj=a.object or SCRATCH/'store.o';exe=(a.exe or SCRATCH/'replay').resolve()
    if a.kind=='compile':
      run(['/usr/bin/c++',*FLAGS,'-c',SRC[1],'-o',obj],True)
      run(['/usr/bin/c++',*FLAGS,SRC[2],obj,*LIBS,'/usr/lib/x86_64-linux-gnu/libpng16.so.16','-lz','-lssl','-lcrypto','-ldl','-lm','-o',exe],True);return
    if a.kind=='format':run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*SRC],True);return
    symbols=run(['nm','--defined-only',obj]);assert MANGLED in [x.split()[-1] for x in symbols.splitlines() if x.split()]
    if a.kind=='symbols':print(symbols);return
    started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*SRC],True)
    fixture=json.loads((ROOT/TEST/'fixtures.json').read_text());current_native=[native.execute(False),native.execute(True)]
    assert current_native==fixture['native']
    observations=[]
    for case in fixture['cases']:
      ops=[x['operation'] for x in current_native[int(case['args'][0])]['calls']]
      assert ops==case['operations_from_native']
      expected=run([exe,'provider',*case['args'],*ops]);assert expected==case['provider_stdout']
      actual=run([exe,'application',*case['args']]);assert actual==expected,(case,actual,expected)
      observations.append({'args':case['args'],'operations':ops,'provider':expected,'application':actual})
    sources={str(Path(s).relative_to('uc-library')):sha(s) for s in SRC}
    deps={str(Path('third_party/ccl-framework/core/portable')/s):sha(Path('third_party/ccl-framework/core/portable')/s) for s in ['coreparams.h','coreparams.cpp','corecomponent.h','corecomponent.cpp','coreparaminfo.h']}
    domain=fixture['domain']+' Valid caller-owned NumericParam, no derived overrides, no replacement/destruction from callbacks. Capture real controller/observer value/message/order; clamp current to[-2,2], reset real default, edit=true then false; stable binding second read retained.'
    limitations=['Provisional void return; original ordinary return/inheritance/class fields/layout/ARM ABI unresolved.','No original construction or hardware behavior claimed.','Core original instructions never executed. Actual pinned SDK providers define value/controller/observer behavior, intentionally source port.','Core-boundary effects replayed after capturing whole body because stable non-reentrant binding and application has no parameter-value-dependent control. Unknown derived overrides, callback replacement/destruction and exceptional paths excluded.']
    entry={'original_elf_sha256':native.ELF_SHA,'mangled':MANGLED,'original_address':442264,'portable_ready':False,'cpp_compiled':True,'mangling_namespace_checked':True,'sources':sources,'repository_sources':deps,'domain':domain,'declaration_uncertainties':limitations[:1]}
    proof={'version':1,'task_id':TASK,'session_id':'/root/rolling10_panel','start_utc':started,'end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':sys.argv,'canonical_binding_pending':not bool(a.integration),'original_elf_sha256':native.ELF_SHA,'portable_ready':False,'cpp_compiled':True,'format_check_passed':True,'mangling_namespace_checked':True,'behavior_validation_passed':True,'sources':sources,'repository_sources':deps,'domain':domain,'proposed_readiness':{'ready':[],'pending':[entry]},'native':current_native,'real_provider_and_application_cases':observations,'case_count':len(observations),'fixture_sha256':sha(TEST/'fixtures.json'),'producers':{str(TEST/s):sha(TEST/s) for s in ['native.py','check.py']},'sdk_archives':{str(s):sha(s) for s in LIBS},'executable':{'path':str(exe),'sha256':sha(exe)},'object':{'path':str(obj),'sha256':sha(obj)},'versions':{'compiler':run(['/usr/bin/c++','--version']).splitlines()[0],'formatter':run(['uc-library/.venv/bin/clang-format','--version']).strip()},'limitations':limitations,'original_symbol':MANGLED,'symbols':symbols,'typed_contract':{'path':native.TYPED,'sha256':sha(native.SNAP/native.TYPED)}}
    if a.integration:proof['integration']={'path':str(a.integration),'sha256':sha(a.integration)}
    if a.out:a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(proof,indent=2)+'\n')
    print('PASS80 original-body/real-provider/application cases; namespace/symbol/format verified')
if __name__=='__main__':main()
