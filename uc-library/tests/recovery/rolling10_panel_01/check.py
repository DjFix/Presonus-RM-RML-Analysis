#!/usr/bin/env python3
"""Local and canonical replay entry point; never writes registry or shared files."""
import argparse, datetime, hashlib, json, os, subprocess
from pathlib import Path
import native
ROOT=Path(__file__).resolve().parents[4]
NAME='rolling10_panel_01'
TEST=Path('uc-library/tests/recovery')/NAME
SCRATCH=Path('temp/recovery-work')/NAME
SOURCES=['uc-library/include/presonus/panel/PanelComponent.hpp','uc-library/src/Presonus/Panel/PanelComponent.cpp',str(TEST/'Replay.cpp')]
MANGLED='_ZN8Presonus5Panel14PanelComponent5startEv'
FLAGS=['-std=c++17','-O2','-fno-lto','-UNDEBUG','-fno-rtti','-pthread','-Ulinux','-DCORE_USE_OPENSSL=1','-DPRESONUS_HAS_UPSTREAM_CORE=1','-Iuc-library/include','-Ithird_party/ccl-framework']
LIBS=['temp/provider-baseline08/libpresonus_uc.a','temp/provider-baseline08/libcorelib.a','temp/provider-baseline08/libpresonus_core_allocator.a']
if not (ROOT/LIBS[0]).exists():
    LIBS=['temp/core-upstream/root-integration-01/libpresonus_uc.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(argv):
    print(' '.join(map(str,argv)),flush=True)
    return subprocess.check_output(list(map(str,argv)),cwd=ROOT,env={**os.environ,'TMPDIR':str(ROOT/SCRATCH)},text=True,stderr=subprocess.STDOUT)
def main():
    p=argparse.ArgumentParser();p.add_argument('kind',nargs='?',choices=['format','compile','symbols','replay'],default='replay')
    p.add_argument('--exe',type=Path);p.add_argument('--object',type=Path);p.add_argument('--integration',type=Path);p.add_argument('--out',type=Path)
    a=p.parse_args();os.chdir(ROOT);(ROOT/SCRATCH).mkdir(parents=True,exist_ok=True)
    obj=a.object or SCRATCH/'panel.o';exe=a.exe or SCRATCH/'replay'
    if a.kind=='format':print(run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*SOURCES]));return
    if a.kind=='compile':
        print(run(['/usr/bin/c++',*FLAGS,'-c',SOURCES[1],'-o',obj]))
        print(run(['/usr/bin/c++',*FLAGS,str(TEST/'Replay.cpp'),obj,*LIBS,'/usr/lib/x86_64-linux-gnu/libpng16.so.16','-lz','-lssl','-lcrypto','-ldl','-lm','-o',exe]));return
    symbols=run(['nm','--defined-only',obj]);assert MANGLED in [x.split()[-1] for x in symbols.splitlines() if x.split()]
    if a.kind=='symbols':print(symbols);return
    print(run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*SOURCES]))
    fixture=json.loads((ROOT/TEST/'fixtures.json').read_text())
    observation=native.execute();assert observation==fixture['native']
    output=run([exe.resolve()]);assert output==fixture['portable_stdout'],(output,fixture['portable_stdout'])
    sources={str(Path(s).relative_to('uc-library')):sha(s) for s in SOURCES}
    deps={s:sha(s) for s in ['third_party/ccl-framework/core/portable/corecomponent.h','third_party/ccl-framework/core/portable/corecomponent.cpp','third_party/ccl-framework/core/portable/coreparams.h']}
    domain='12 wrapper register/opaque-pointer cases stopping at tail; exact C1/C2 no-call vptr-install slices; 8 complete original start->activateAll->base doActivate executions on valid vtable/object with stack-only writes and unchanged 256-byte object. Compared with 8 live C++ calls, callback entry counts and preserved independent active flag. Derived doActivate overrides and unencoded return declaration excluded.'
    entry={'original_elf_sha256':native.ELF_SHA,'mangled':MANGLED,'original_address':native.START,'portable_ready':False,'cpp_compiled':True,'mangling_namespace_checked':True,'sources':sources,'repository_sources':deps,'domain':domain,'declaration_uncertainties':['Original unencoded return declaration unresolved; portable void choice. Original inheritance, layout and ARM ABI unproven.']}
    proof={'task_id':NAME,'argv':__import__('sys').argv,'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'session_id':'/root/rolling10_panel','canonical_binding_pending':not bool(a.integration),'original_elf_sha256':native.ELF_SHA,'sources':sources,'repository_sources':deps,'portable_ready':False,'format_check_passed':True,'cpp_compiled':True,'mangling_namespace_checked':True,'behavior_validation_passed':True,'domain':domain,'proposed_readiness':{'ready':[],'pending':[entry]},'native':observation,'portable':{'case_count':8,'stdout':output,'exe':str(exe),'exe_sha256':sha(exe),'object':str(obj),'object_sha256':sha(obj)},'fixtures_sha256':sha(TEST/'fixtures.json'),'producers':{str(TEST/x):sha(TEST/x) for x in ['native.py','check.py']},'versions':{'clang_format':run(['uc-library/.venv/bin/clang-format','--version']).strip(),'compiler':run(['/usr/bin/c++','--version']).splitlines()[0]},'provider_archives':{s:sha(s) for s in LIBS},'limitations':entry['declaration_uncertainties']+observation['limitations']}
    expansion_root=Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/expansions')
    proof['context_expansions']={str(expansion_root/x):sha(expansion_root/x) for x in ['panel-activate/expansion.json','panel-vtable/expansion.json','provider-panel/ROOT_EXPANSION.json','provider-panel/native-context.json']}
    proof['phase_evidence']=json.loads((ROOT/SCRATCH/'phases.json').read_text()) if (ROOT/SCRATCH/'phases.json').exists() else {'session_id':'/root/rolling10_panel','historical_phase_evidence':'Worker HANDOFF local proof contains phase boundaries; canonical replay timestamp current.'}
    if a.integration:proof['integration']={'path':str(a.integration),'sha256':sha(a.integration)}
    if a.out:a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(proof,indent=2)+'\n')
    print('PASS native wrapper/provider and 8 portable calls')
if __name__=='__main__':main()
