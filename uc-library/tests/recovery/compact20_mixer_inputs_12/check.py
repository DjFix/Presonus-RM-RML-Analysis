"""Local checks and fresh canonical proof producer; no registry/global writes."""
import argparse, datetime, hashlib, json, os, pathlib, subprocess, sys, time
ROOT=pathlib.Path(__file__).resolve().parents[4]
TASK=12
NAME=f'compact20_mixer_inputs_{TASK:02}'
TEST=pathlib.Path('uc-library/tests/recovery')/NAME
SCRATCH=pathlib.Path('temp/recovery-work')/NAME
CLASS='MicLineComponent' if TASK==10 else 'TalkbackInputComponent'
SOURCES=[f'uc-library/include/presonus/mixer/{CLASS}.hpp',f'uc-library/src/Presonus/Mixer/{CLASS}.cpp']
CPP=SOURCES+[str(TEST/'Replay.cpp')]
ELF_SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
MANGLES={10:'_ZN8Presonus5Mixer16MicLineComponent37calculateDigitalMicPreampGainDivisionEPfS2_f',12:'_ZN8Presonus5Mixer22TalkbackInputComponent14isPostFaderAuxEi',13:'_ZN8Presonus5Mixer22TalkbackInputComponent18addRemoveObserversEb'}
PROVIDERS=[] if TASK==10 else ['third_party/ccl-framework/core/portable/corecomponent.h','third_party/ccl-framework/core/portable/corecomponent.cpp','third_party/ccl-framework/core/portable/coreparams.h','third_party/ccl-framework/core/portable/coreparams.cpp','third_party/ccl-framework/core/portable/coreparaminfo.h','third_party/ccl-framework/core/portable/coretypeinfo.h','third_party/ccl-framework/core/public/corevector.h']
DEPENDENCIES=[] if TASK==10 else ['uc-library/include/presonus/mixer/ChannelComponent.hpp','uc-library/src/Presonus/Mixer/ChannelComponent.cpp','uc-library/include/presonus/mixer/MixerComponentBase.hpp']
def digest(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def run(argv,**kw):
    before=time.monotonic();p=subprocess.run([str(x) for x in argv],cwd=ROOT,text=True,capture_output=True,**kw)
    if p.returncode:raise RuntimeError(json.dumps({'argv':[str(x) for x in argv],'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}))
    return {'argv':[str(x) for x in argv],'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'seconds':time.monotonic()-before}
def compile_local():
    scratch=ROOT/SCRATCH;scratch.mkdir(parents=True,exist_ok=True);os.environ['TMPDIR']=str(scratch)
    flags=['/usr/bin/c++','-std=c++17','-O2','-fno-rtti','-DNDEBUG=1','-DPRESONUS_HAS_UPSTREAM_CORE=1','-DCORE_USE_OPENSSL=1','-Ulinux','-fno-fast-math','-ffp-contract=off','-pthread','-Iuc-library/include','-Ithird_party/ccl-framework']
    obj=SCRATCH/'production.o';commands=[run(flags+['-c',SOURCES[1],'-o',str(obj)])]
    libs=[] if TASK==10 else ['-Wl,--start-group','temp/provider-baseline08/libpresonus_rm_components.a','temp/provider-baseline08/libcorelib.a','temp/provider-baseline08/libpresonus_core_allocator.a','-Wl,--end-group','-lz','-lssl','-lcrypto','-ldl']
    commands.append(run(flags+[str(TEST/'Replay.cpp'),str(obj)]+libs+['-o',str(SCRATCH/'replay')]))
    (scratch/'compile.json').write_text(json.dumps(commands,indent=2)+'\n');return commands

def symbols(exe):
    result=run(['/usr/bin/nm','--defined-only',exe]);assert MANGLES[TASK] in {line.split()[-1] for line in result['stdout'].splitlines() if line.split()},'Original mangled identity absent'
    return {'argv':result['argv'],'mangling_namespace_checked':True,'compiled_mangled_names_matched':True,'mangled':MANGLES[TASK],'executable_sha256':digest(exe)}
def replay(exe,fixtures):
    data=json.loads(fixtures.read_text());assert data['task']==TASK and data['elf_sha256']==ELF_SHA;assert data['producer_sha256']==digest(ROOT/TEST/'native.py'),'Fixture producer changed'
    cases=data['cases']
    if TASK==10:
        text=''.join(f"{c['input_bits']} {int(c['alias'])}\n" for c in cases);want=[[c['status']]+c['outputs'] for c in cases]
    elif TASK==12:
        text=''.join(f"{c['value']} {c['argument']}\n" for c in cases);want=[[c['result']] for c in cases]
    else:
        text=''.join(f"{int(c['settings_present'])} {len(c['steps'])} "+' '.join(str(int(x['add'])) for x in c['steps'])+'\n' for c in cases);want=[[v for step in c['steps'] for v in step['counts']] for c in cases]
    result=run([exe],input=text);got=[[int(v) for v in line.split()] for line in result['stdout'].splitlines()]
    assert len(got)==len(want),(len(got),len(want))
    for ix,(a,b) in enumerate(zip(got,want)):
        assert a==b,{'case':ix,'actual':a,'native':b}
    return {'argv':[str(pathlib.Path(__file__).relative_to(ROOT)),'--replay','--executable',str(exe),'--fixtures',str(fixtures)],'actual_executable_argv':result['argv'],'input_sha256':hashlib.sha256(text.encode()).hexdigest(),'output_sha256':hashlib.sha256(result['stdout'].encode()).hexdigest(),'cases':len(cases),'cpp_differential_passed':True,'seconds':result['seconds'],'domain':data['metadata']['boundary'],'native_origin':{'elf_sha256':data['elf_sha256'],'range':data['range'],'producer_sha256':data['producer_sha256'],'engine':data['engine']}}
def proof(path,exe,fixtures,obj=None,integration=None,supplied_outputs=False):
    assert not path.exists(),'Fresh proof path required'
    if supplied_outputs:
        assert obj is not None and integration is not None, 'Explicit executable proof requires --object and fresh --integration'
        assert obj.is_file() and integration.is_file(), 'Supplied object/integration must exist'
        receipt=json.loads(integration.read_text())
        assert isinstance(receipt,dict) and receipt, 'Nonempty actual integration receipt required'
    before=time.monotonic();s=symbols(exe);p=replay(exe,fixtures)
    bindings={x:digest(ROOT/x) for x in SOURCES+DEPENDENCIES+[str(TEST/'Replay.cpp'),str(TEST/'native.py'),str(TEST/'check.py'),str(fixtures.relative_to(ROOT))]}
    formatter=os.environ.get('CLANG_FORMAT','/home/rs/projects/opencs/ai-line-analysis/uc-library/.venv/bin/clang-format')
    fm=run([formatter,'--style=file','--fallback-style=LLVM','--dry-run','--Werror']+CPP)
    f={'original_elf_sha256':ELF_SHA,'mangled':MANGLES[TASK],'cpp_compiled':True,'mangling_namespace_checked':True,'portable_ready':False,'domain':p['domain'],'declaration_uncertainties':['Original return declaration unresolved; source-port return chosen explicitly. Original layout, inheritance and ARM ABI not established.'],'cpp_differential_passed':True}
    proposal={**f,'sources':{x.removeprefix('uc-library/'):v for x,v in bindings.items()},'repository_sources':{x:digest(ROOT/x) for x in PROVIDERS}}
    d={'version':1,'task_id':NAME,'provider_thread_id':os.environ.get('CODEX_THREAD_ID'),'implementation_start_utc':'2026-11-13T17:23:46.894514+00:00','produced_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'producer':{'path':str(pathlib.Path(__file__).relative_to(ROOT)),'sha256':digest(__file__)},'cpp_differential_passed':True,'compiled_mangled_names_matched':True,'mangling_namespace_checked':True,'functions':[f],'sources':bindings,'repository_sources':proposal['repository_sources'],'fixture':{'path':str(fixtures.relative_to(ROOT)),'sha256':digest(fixtures)},'executable':{'path':str(exe),'sha256':digest(exe)},'symbol_check':s,'replay':p,'format':{'formatter_version':run([formatter,'--version'])['stdout'].strip(),'check':fm},'proposed_readiness':{'canonical_binding_pending':True,'ready':[],'pending':[proposal]},'scope':'Actual fresh portable/native-boundary differential; not original declarations, firmware Core behavior, ARM ABI, hardware, global integration or readiness admission.'}
    if obj:d['object']={'path':str(obj),'sha256':digest(obj)}
    if integration:d['integration']={'path':str(integration),'sha256':digest(integration)}
    d['implementation_end_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    d['compiler_version']=run(['/usr/bin/c++','--version'])['stdout'].splitlines()[0]
    compile_record=ROOT/SCRATCH/'compile.json'
    if not supplied_outputs and compile_record.exists():d['local_compile_commands']=json.loads(compile_record.read_text())
    d['remarks']=[{'date':d['produced_utc'],'original_elf_sha256':ELF_SHA,'mangled':MANGLES[TASK],'status':'compiled_declaration_pending','observation':'Bounded native/provider differential passed. Original return declaration remains unresolved; source-port API is explicit. No original class layout/inheritance/ARM ABI or hardware claim.','retry_condition':'Independent original return declaration evidence for promotion; expand behavior only with new native/provider domains.'}]
    if TASK==10:d['remarks'].append({'date':d['produced_utc'],'original_elf_sha256':ELF_SHA,'mangled':MANGLES[TASK],'status':'resolved_implementation_discrepancy','observation':'Initial research plan confused upper gain bound60.f literal at0x41b94 with nearest-distance initialization100.f at0x41b98. Native differential rejected100 before handoff. Production corrected to60; fixture includes60, adjacent float values,61 and100. Original frozen research is preserved.','resolution':'Exact ELF literal bytes and independently regenerated passing native fixture.'})
    d['proof_mode']='supplied_outputs' if supplied_outputs else 'worker_baseline'
    if supplied_outputs:
        # The caller supplies actual fresh build outputs and its integration
        # receipt. Never attribute worker-local archive linkage to that build.
        d['provider_provenance']={'kind':'supplied_build_outputs_and_source_bindings','integration':d['integration'],'executable':d['executable'],'object':d['object'],'repository_sources':d['repository_sources']}
        d['scope']+=' Supplied-output replay binds the actual integration receipt; it does not independently establish all global integration gates or readiness.'
    else:
        d['provider_archives']={x:digest(ROOT/x) for x in ['temp/provider-baseline08/libpresonus_rm_components.a','temp/provider-baseline08/libcorelib.a','temp/provider-baseline08/libpresonus_core_allocator.a']}
        d['provider_provenance']={'kind':'worker_baseline_linkage','path':'temp/provider-baseline08/PROVENANCE.json','sha256':digest(ROOT/'temp/provider-baseline08/PROVENANCE.json')}
        d['canonical_replay_pending']=True
        history=ROOT/SCRATCH/'proof-portability-before01/PRESERVATION.json'
        if history.exists():d['proof_revision_history']={'path':str(history.relative_to(ROOT)),'sha256':digest(history),'meaning':'Exact historical producer/proof/handoff retained; historical execution is never attributed to this changed producer.'}

    d['seconds']=time.monotonic()-before;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(d,indent=2)+'\n');return d
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--compile',action='store_true');a.add_argument('--symbols',action='store_true');a.add_argument('--replay',action='store_true');a.add_argument('--native',action='store_true');a.add_argument('--elf',type=pathlib.Path);a.add_argument('--executable',type=pathlib.Path);a.add_argument('--fixtures',type=pathlib.Path,default=TEST/'fixtures.json');a.add_argument('--proof',type=pathlib.Path);a.add_argument('--object',type=pathlib.Path);a.add_argument('--integration',type=pathlib.Path);x=a.parse_args();os.chdir(ROOT)
    exe=(ROOT/(x.executable or SCRATCH/'replay')).resolve();fixtures=(ROOT/x.fixtures).resolve();out={}
    if x.compile:out['compile']=compile_local()
    if x.native:
        assert x.elf;out['native']=run([sys.executable,TEST/'native.py','--elf',x.elf,'--out',SCRATCH/'native-recheck.json']);fresh=json.loads((ROOT/SCRATCH/'native-recheck.json').read_text());sealed=json.loads(fixtures.read_text());assert fresh['cases']==sealed['cases'] and fresh['range']==sealed['range'],'Native fixture changed'
    if x.symbols:out['symbols']=symbols(exe)
    if x.replay:out['replay']=replay(exe,fixtures)
    if x.proof:out['proof']=proof((ROOT/x.proof).resolve(),exe,fixtures,x.object,x.integration,supplied_outputs=x.executable is not None)
    print(json.dumps(out))
