import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[4];T=Path(__file__).resolve().parent;TASK=T.name;O=R/'temp/recovery-work'/TASK;O.mkdir(parents=True,exist_ok=True)
SOURCES=['uc-library/include/presonus/panel/StormFrontPanelComponent.hpp','uc-library/src/Presonus/Panel/StormFrontPanelComponent.cpp'];OWNED=SOURCES+[str((T/'Replay.cpp').relative_to(R))]
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(argv,input=None):
 print(json.dumps(list(map(str,argv))),flush=True);p=subprocess.run(list(map(str,argv)),cwd=R,input=input,capture_output=True,text=True,env={**os.environ,'TMPDIR':str(O)});print(p.stdout,end='');print(p.stderr,end='',file=sys.stderr);p.check_returncode();return p.stdout
def main():
 p=argparse.ArgumentParser();p.add_argument('mode',nargs='?',default='replay');p.add_argument('--exe');p.add_argument('--object');p.add_argument('--integration');p.add_argument('--out');a=p.parse_args();import native
 if a.mode=='format':run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*OWNED]);return
 fixture=json.loads((T/'fixtures.json').read_text())
 if a.mode=='native':assert native.generate()==fixture;return
 if a.mode=='compile':
  flags=['c++','-std=c++17','-O0','-ffunction-sections','-fdata-sections','-Iuc-library/include']
  run([*flags,'-c',SOURCES[1],'-o',O/'production.o']);run([*flags,'-c',OWNED[2],'-o',O/'driver.o']);run(['c++',O/'production.o',O/'driver.o','-Wl,--gc-sections','-o',O/'replay']);return
 obj=Path(a.object) if a.object else O/'production.o';exe=Path(a.exe) if a.exe else O/'replay'
 symbols=run(['nm','--defined-only',obj]);names={l.split()[-1] for l in symbols.splitlines() if l.split()};assert native.NAME in names
 for t in fixture['tables'].values():assert t['mangled'] in names
 if a.mode=='symbols':return
 assert native.generate()==fixture
 output=run([exe],''.join(str(c['group'])+'\n' for c in fixture['cases']));lines=output.splitlines();assert len(lines)==len(fixture['cases'])
 for c,line in zip(fixture['cases'],lines):assert list(map(int,line.split()))==[c['count']]+[v for table in c.get('values',[]) for v in table]
 domain='51 ARM/host group inputs: 0,1,2, unknown negative/positive, INT_MIN/MAX and seeded 32-bit samples; exact selected table contents/count; unknown references unchanged; six complete original static arrays range/hash verified; no external calls.'
 limitations=['Provisional void return: original ordinary return unresolved','Portable source port; original class layout/ARM ABI and hardware not established','Distinct valid output references tested; pointer identities normalized to full table contents']
 sources={str(Path(x).relative_to('uc-library')):digest(R/x) for x in SOURCES}
 proof=dict(task_id=TASK,original_elf_sha256=native.SHA,mangled_names=[native.NAME],native=fixture,canonical_binding_pending=not bool(a.integration),compiled_mangled_names_matched=True,cpp_differential_passed=True,portable_ready=False,validation_domain=domain,limitations=limitations,sources=sources,repository_sources={},object=dict(path=str(obj),sha256=digest(obj)),executable=dict(path=str(exe),sha256=digest(exe)),formatter=run(['uc-library/.venv/bin/clang-format','--version']).strip())
 if a.integration:proof['integration']=dict(path=a.integration,sha256=digest(R/a.integration))
 proof['proposed_readiness']=dict(ready=[],pending=[dict(original_elf_sha256=native.SHA,mangled=native.NAME,original_address=native.ADDRESS,sources=sources,domain=domain,declaration_uncertainties=limitations,canonical_binding_pending=not bool(a.integration))])
 for entry in proof['proposed_readiness']['pending']:
  entry.update(portable_ready=False,cpp_compiled=True,mangling_namespace_checked=True,repository_sources=proof['repository_sources'])
 if a.out:Path(a.out).write_text(json.dumps(proof,indent=2)+'\n')
if __name__=='__main__':main()
