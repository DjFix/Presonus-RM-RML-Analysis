import argparse, hashlib, json, os, subprocess, datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
TASK='compact20_mixer_cascade_01'
TEST=Path('uc-library/tests/recovery')/TASK
SOURCES=['uc-library/include/presonus/mixer/CascadeLinkHandler.hpp','uc-library/src/Presonus/Mixer/CascadeLinkHandler.cpp',str(TEST/'Replay.cpp')]
MANGLED='_ZN8Presonus5Mixer18CascadeLinkHandler13connectDeviceEv'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(argv):
    r=subprocess.run([str(x) for x in argv],cwd=ROOT,text=True,capture_output=True)
    if r.returncode: raise RuntimeError(str(argv)+'\n'+r.stdout+r.stderr)
    return r.stdout

def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['compile','symbols','replay','proof'],required=True);p.add_argument('--executable',type=Path);p.add_argument('--fixtures',type=Path,default=ROOT/TEST/'fixtures.json');p.add_argument('--proof-out',type=Path);p.add_argument('--integration',type=Path);p.add_argument('--object',type=Path);p.add_argument('--elf',type=Path,default=Path('/home/rs/projects/opencs/ai-line-analysis/rootfs/RML16AI_Rack_13731/home/root/mixer'));a=p.parse_args()
    scratch=ROOT/'temp/recovery-work'/TASK/'implementation';scratch.mkdir(parents=True,exist_ok=True)
    external_build = a.executable is not None or a.object is not None
    if a.mode == 'proof' and external_build:
        if a.executable is None or a.object is None or a.integration is None:
            p.error('external canonical proof requires --executable, --object and fresh --integration receipt')
        if not a.integration.is_file():
            p.error('external canonical integration receipt is absent')
    exe=a.executable or scratch/'replay';obj=a.object or scratch/'CascadeLinkHandler.o'
    cpp=ROOT/SOURCES[1];replay=ROOT/SOURCES[2]
    flags=['-std=c++17','-DNDEBUG','-Ulinux','-pthread','-I'+str(ROOT/'uc-library/include'),'-I'+str(ROOT/'third_party/ccl-framework')]
    if a.mode=='compile':
        run(['/usr/bin/c++',*flags,'-c',cpp,'-o',obj])
        run(['/usr/bin/c++',*flags,replay,obj,ROOT/'temp/provider-baseline08/libcorelib.a',ROOT/'temp/provider-baseline08/libpresonus_core_allocator.a','-ldl','-o',exe]);print('compiled',exe);return
    symbols=run(['/usr/bin/nm','--defined-only',obj])
    assert MANGLED in {line.split()[-1] for line in symbols.splitlines() if line.split()}, 'exact symbol absent'
    if a.mode=='symbols':print('matched',MANGLED);return
    fixture=json.loads(a.fixtures.read_text());assert fixture['mangled']==MANGLED
    import importlib.util
    spec=importlib.util.spec_from_file_location('cascade_native',ROOT/TEST/'native.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    assert module.observe(a.elf)==fixture, 'fresh original instructions differ from bound fixtures'
    outcomes=[]
    for case in fixture['cases']:
        argv=[exe,case['repeats'],case['id'],case['present'],len(case['primary']),*case['primary'],*case['pending']]
        text=run(argv)
        outcomes.append(dict(argv=[str(x) for x in argv],returncode=0,stdout_sha256=hashlib.sha256(text.encode()).hexdigest()))
        actual=json.loads(next(line[7:] for line in text.splitlines() if line.startswith('RESULT ')))
        # Expected insertion identities come from ARM call arguments, not C++.
        calls=[e['value'] for e in case['events'] if e['kind']=='add']
        assert all(e['receiver']==0x104 for e in case['events'] if e['kind']=='add')
        assert actual==case['pending']+calls,(case,actual)
        diagnostic=[e for e in case['events'] if e['kind']=='debug']
        expected=['CascadeLinkHandler::connect to client id=%d\n'%((e['id']+2**31)%2**32-2**31) for e in diagnostic]
        assert text==''.join(expected)+'RESULT '+json.dumps(actual,separators=(',',':'))+'\n'
    print('passed',len(fixture['cases']),'original application/native-call versus actual CCL C++ cases')
    if a.mode=='proof':
        assert a.proof_out and not a.proof_out.exists(),'proof output must be new'
        sources={x[11:]:sha(ROOT/x) for x in SOURCES}
        for name in ['native.py','check.py','fixtures.json']:sources[str(TEST/name)[11:]]=sha(ROOT/TEST/name)
        providers={x:sha(ROOT/x) for x in ['third_party/ccl-framework/core/public/corevector.h','third_party/ccl-framework/core/system/coredebug.cpp','third_party/ccl-framework/core/system/coredebug.h']}
        run(['/home/rs/projects/opencs/ai-line-analysis/uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*[ROOT/x for x in SOURCES]])
        dependency_text=run(['/usr/bin/c++',*flags,'-MM',cpp]).replace('\\\n',' ')
        import shlex
        for token in shlex.split(dependency_text.split(':',1)[1]):
            dep=Path(token).resolve()
            if dep.is_relative_to(ROOT/'third_party/ccl-framework'):
                providers[str(dep.relative_to(ROOT))]=sha(dep)
        domain='60 well-formed vector cases, 0..20 borrowed primary pointers, null/duplicate identities, 0..5 preexisting pending entries, 1..3 repetitions, nullable diagnostic IDs; successful CCL allocation only; no concurrent mutation.'
        record=dict(original_elf_sha256=fixture['original_elf_sha256'],mangled=MANGLED,sources=sources,repository_sources=providers,domain=domain,portable_ready=False,cpp_compiled=True,mangling_namespace_checked=True,declaration_uncertainties=['Original unencoded return type remains unresolved; portable source chooses void. Original fields/inheritance/layout/lifecycle not recovered.'])
        proof=dict(version=1,session_id=os.environ.get('CODEX_THREAD_ID'),implementation_start_utc='2026-11-13T17:23:32Z',implementation_end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),cpp_differential_passed=True,compiled_mangled_names_matched=True,functions=[dict(record,cases=len(fixture['cases']),original_address=fixture['address'],original_size=fixture['size'],file_offset=fixture['file_offset'],range_sha256=fixture['range_sha256'],oracle=fixture['native_oracle'])],source_hashes=sources,repository_sources=providers,executable=dict(path=str(exe),sha256=sha(exe)),object=dict(path=str(obj),sha256=sha(obj)),fixture=dict(path=str(a.fixtures),sha256=sha(a.fixtures)),producer=dict(path=str(TEST/'check.py'),sha256=sha(__file__)),replay_outcomes=outcomes,native_fixture_provenance=dict(elf_path=str(a.elf),elf_sha256=fixture['original_elf_sha256'],range_sha256=fixture['range_sha256'],producer_sha256=fixture['producer_sha256'],unicorn_version=fixture['unicorn_version'],fresh_reexecution_passed=True),provider_dependency_probe_flags=flags,format_version=run(['/home/rs/projects/opencs/ai-line-analysis/uc-library/.venv/bin/clang-format','--version']).strip(),proposed_readiness=dict(canonical_binding_pending=True,ready=[],pending=[record]),limitations=['No Core firmware execution; two capture boundaries record actual original caller arguments. Real CCL vector/debug providers execute in portable replay. Allocation failures, concurrent mutation, ARM ABI and hardware excluded.'])
        if external_build:
            proof['build_origin'] = 'supplied external executable/object and integration receipt; no worker baseline linking claim'
            proof['integration_reference'] = dict(path=str(a.integration), sha256=sha(a.integration))
        else:
            proof['build_origin'] = 'worker local compile mode using immutable provider baseline08'
            proof['compile_flags'] = flags
            proof['provider_archives'] = {str(x):sha(ROOT/x) for x in ['temp/provider-baseline08/libcorelib.a','temp/provider-baseline08/libpresonus_core_allocator.a']}
            proof['provider_provenance'] = dict(path='temp/provider-baseline08/PROVENANCE.json',sha256=sha(ROOT/'temp/provider-baseline08/PROVENANCE.json'))
            if a.integration:
                proof['integration_reference'] = dict(path=str(a.integration),sha256=sha(a.integration))
        a.proof_out.parent.mkdir(parents=True,exist_ok=True);a.proof_out.write_text(json.dumps(proof,indent=2)+'\n')
if __name__=='__main__':main()
