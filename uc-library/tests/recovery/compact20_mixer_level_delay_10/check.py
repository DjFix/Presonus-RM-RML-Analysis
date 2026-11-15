"""Worker replay adapter and fresh proof producer, usable with Root's built executable."""
import argparse, datetime, hashlib, json, platform, shlex, subprocess, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
TASK=Path(__file__).parent.name
INDEX=10
LIB=ROOT/'uc-library'
HEADER=LIB/'include/presonus/mixer/DelayComponent.hpp'
SOURCE=LIB/'src/Presonus/Mixer/DelayComponent.cpp'
def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(argv,**kw):
    start=time.monotonic();r=subprocess.run([str(x) for x in argv],text=True,capture_output=True,check=True,**kw)
    return r, {'argv':[str(x) for x in argv],'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'seconds':time.monotonic()-start}
def bindings(paths): return {str(p.relative_to(ROOT)):digest(p) for p in paths}
def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['compile','symbols','replay','proof'],required=True);p.add_argument('--executable',required=True);p.add_argument('--object');p.add_argument('--fixtures',required=True);p.add_argument('--elf');p.add_argument('--proof-out');p.add_argument('--integration-proof');p.add_argument('--compile-log');p.add_argument('--formatter',default='/home/rs/projects/opencs/ai-line-analysis/uc-library/.venv/bin/clang-format');a=p.parse_args()
    exe=Path(a.executable).resolve();fixture=Path(a.fixtures).resolve();data=json.loads(fixture.read_text());commands=[]
    if a.mode=='compile':
        obj=Path(a.object).resolve() if a.object else exe.parent/'DelayComponent.o';exe.parent.mkdir(parents=True,exist_ok=True);obj.parent.mkdir(parents=True,exist_ok=True)
        for argv in [['/usr/bin/g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I'+str(LIB/'include'),'-c',SOURCE,'-o',obj],['/usr/bin/g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I'+str(LIB/'include'),Path(__file__).parent/'Replay.cpp',obj,'-o',exe]]:
            _,log=run(argv);commands.append(log)
        compilation={'commands':commands,'source_bindings':bindings([HEADER,SOURCE,Path(__file__).parent/'Replay.cpp']),'executable_sha256':digest(exe),'object_sha256':digest(obj)}
        log_path=exe.parent/'compile.json'
        if log_path.exists():
            previous=json.loads(log_path.read_text())
            assert all(previous[k]==compilation[k] for k in ['source_bindings','executable_sha256','object_sha256']),'Changed compile inputs/output require NEW scratch directory; preserve prior evidence'
        else: log_path.write_text(json.dumps(compilation,indent=2)+'\n')
        print(json.dumps(commands));return
    names,log=run(['/usr/bin/nm','--defined-only',exe]);commands.append(log)
    assert data['mangled'] in {line.split()[-1] for line in names.stdout.splitlines() if line.split()},'Original mangled name absent'
    if a.mode=='symbols': print('Matched exact original:',data['mangled']);return
    if INDEX==11:
        r,log=run([exe]);commands.append(log);lines=r.stdout.splitlines();assert lines.pop(0)=='stable 1','Table identity must be stable'
        observed=[]
        for line in lines:
            fields=shlex.split(line);assert len(fields)==5
            observed.append({'family':int(fields[0]),'index':int(fields[1]),'effect_type_bits':int(fields[2]),'value_bits':int(fields[3]),'name':fields[4]})
        expected=[{k:v for k,v in row.items() if k!='original_string_address'} for row in data['rows']]
        assert observed==expected,'Relocation-normalized table/strings mismatch';case_count=len(observed);domain='21 complete application table rows including sentinel, both float bit patterns, exact UTF-8 strings and stable repeated portable pointer; original returned table address independently executed.'
    else:
        stdin=''.join(str(c['input_r1_u32'])+'\n' for c in data['cases']);r,log=run([exe],input=stdin);commands.append(log);observed=[int(line) for line in r.stdout.splitlines()];assert observed==[c['output_r0_u32'] for c in data['cases']],'Original instruction output mismatch';case_count=len(observed);domain='All integer branch cases and adjacent values, INT_MIN/INT_MAX/wrap boundaries, deterministic256 arbitrary32-bit patterns; exact original r0 bits, no nonstack writes or receiver dereference.'
    print('Differential replay passed:',case_count,'cases:',data['mangled'])
    if a.mode=='proof':
        assert a.proof_out and a.elf,'Proof requires explicit NEW output and exact source ELF'
        out=Path(a.proof_out);assert not out.exists(),'Refuse proof overwrite';out.parent.mkdir(parents=True,exist_ok=True)
        _,log=run([sys.executable,Path(__file__).parent/'native.py','--elf',a.elf,'--verify',fixture]);commands.append(log)
        _,log=run([a.formatter,'--style=file','--fallback-style=LLVM','--dry-run','--Werror',HEADER,SOURCE,Path(__file__).parent/'Replay.cpp']);commands.append(log)
        fmt,_=run([a.formatter,'--version']);compiler,_=run(['/usr/bin/g++','--version'])
        sources=bindings([HEADER,SOURCE,Path(__file__),Path(__file__).parent/'native.py',Path(__file__).parent/'Replay.cpp',fixture]);uncertainties=['Original unencoded return declaration unresolved.','Original class layout, inheritance and ARM ABI unverified.']
        if INDEX==11:uncertainties+=['Original pointer/row type and const qualifications unresolved; table representation is explicitly independent.']
        if INDEX==12:uncertainties+=['Original EffectType enumerator names, enum declaration and signed return declaration unresolved; fixed-width enum is portable choice.']
        record={'original_elf_sha256':data['original_elf_sha256'],'mangled':data['mangled'],'sources':{str(Path(k).relative_to('uc-library')):v for k,v in sources.items()},'repository_sources':{},'domain':domain,'portable_ready':False,'cpp_compiled':True,'mangling_namespace_checked':True,'declaration_uncertainties':uncertainties}
        proof={'version':1,'task_id':TASK,'producer_session_id':'01a1d59d-dfb8-7812-a170-b0cd7e14513c','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'original_elf_sha256':data['original_elf_sha256'],'mangled':data['mangled'],'functions':[dict(record,original_range=data['original_range'],case_count=case_count,cpp_differential_passed=True,compiled_mangled_names_matched=True)],'cpp_differential_passed':True,'compiled_mangled_names_matched':True,'cpp_compiled':True,'portable_ready':False,'original_arm_abi_verified':False,'hardware_verified':False,'source_bindings':sources,'fixture':{'path':str(fixture.relative_to(ROOT)),'sha256':digest(fixture),'native_oracle':data['oracle'],'original_range':data['original_range'],'native_case_count':len(data['cases']),'portable_case_count':case_count},'commands':commands,'tools':{'formatter':fmt.stdout.strip(),'compiler':compiler.stdout.splitlines()[0],'python':platform.python_version()},'executable':{'path':str(exe),'sha256':digest(exe)},'proposed_readiness':{'canonical_binding_pending':True,'ready':[],'pending':[record]},'limitations':uncertainties,'canonical_integration_completed':False}
        compile_log=Path(a.compile_log) if a.compile_log else exe.parent/'compile.json'
        if compile_log.is_file():
            compilation=json.loads(compile_log.read_text())
            assert all(digest(ROOT/k)==v for k,v in compilation['source_bindings'].items()),'Stale compile log sources'
            assert compilation['executable_sha256']==digest(exe),'Stale compile log executable'
            proof['compilation']=compilation
            proof['compile_log']={'path':str(compile_log.resolve()),'sha256':digest(compile_log)}
        if a.object:proof['compiled_object']={'path':str(Path(a.object).resolve()),'sha256':digest(a.object)}
        if a.integration_proof:proof['fresh_integration_reference']={'path':str(Path(a.integration_proof).resolve()),'sha256':digest(a.integration_proof)}
        out.write_text(json.dumps(proof,indent=2)+'\n')
if __name__=='__main__': main()
