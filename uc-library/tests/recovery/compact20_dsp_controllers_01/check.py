import argparse,datetime,hashlib,json,os,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=Path.cwd();CANON=Path('/home/rs/projects/opencs/ai-line-analysis');KIND=int(HERE.name[-2:]);SCRATCH=ROOT/'temp/recovery-work/compact20-dsp-implementation'/HERE.name
SOURCES=['uc-library/include/presonus/surface/TransportHandler.hpp','uc-library/src/Presonus/Surface/TransportHandler.cpp','uc-library/include/presonus/surface/DAWDialogHandler.hpp','uc-library/src/Presonus/Surface/DAWDialogHandler.cpp',str(HERE/'Replay.cpp')]
PROVIDERS=['coreparams.h','coreparams.cpp','coreparaminfo.h','corecomponent.h','corecomponent.cpp']
PACKET=CANON/'temp/recovery-work/compact-10x20-20261113/generated-implementation40/prepared03/packets'/HERE.name
TARGET=json.loads((PACKET/'request.json').read_text())['targets'][0]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(argv):
 argv=list(map(str,argv));print(json.dumps(argv),flush=True);r=subprocess.run(argv,text=True,capture_output=True,env={**os.environ,'TMPDIR':str(SCRATCH)});print(r.stdout,end='');print(r.stderr,end='');r.check_returncode();return r.stdout

def main():
 p=argparse.ArgumentParser();p.add_argument('gate',choices=['format','compile','symbols','replay']);p.add_argument('--fixtures',default=str(HERE/'fixtures.json'));p.add_argument('--executable',default=str(SCRATCH/'replay'));p.add_argument('--proof-out');p.add_argument('--integration-proof');p.add_argument('--object',action='append',default=[]);a=p.parse_args();SCRATCH.mkdir(parents=True,exist_ok=True)
 if a.gate=='format':run([CANON/'uc-library/.venv/bin/clang-format','--version']);run([CANON/'uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*SOURCES]);return
 if a.gate=='compile':
  flags=['-std=c++20','-fno-rtti','-O2','-ffunction-sections','-fdata-sections','-pthread','-Ulinux','-DCORE_USE_OPENSSL=1','-DPRESONUS_HAS_UPSTREAM_CORE=1','-Iuc-library/include','-Ithird_party/ccl-framework','-I'+str(CANON/'temp/core-upstream/root-integration-01/upstream-core/sdk/include/presonus-core-5')];objects=[]
  for src in SOURCES[1:4:2]:
   obj=SCRATCH/(Path(src).stem+'.o');run(['/usr/bin/c++',*flags,'-c',src,'-o',obj]);objects.append(obj)
  libs=[ROOT/'temp/provider-baseline08'/n for n in ['libcorelib.a','libpresonus_core_allocator.a']]
  run(['/usr/bin/c++',*flags,'-DTASK_NUMBER='+str(KIND),HERE/'Replay.cpp',*objects,'-Wl,--gc-sections','-Wl,--start-group',*libs,'-Wl,--end-group','-lz','-lssl','-lcrypto','-ldl','-lm','-o',a.executable]);return
 if a.gate=='symbols':
  text=run(['/usr/bin/nm','--defined-only',SCRATCH/('TransportHandler.o' if KIND<10 else 'DAWDialogHandler.o')]);assert TARGET['mangled'] in {l.split()[-1] for l in text.splitlines() if l.split()};return
 fixture=json.loads(Path(a.fixtures).read_text());assert fixture['producer_sha256']==sha(HERE/'native.py');assert fixture['target']==TARGET;commands=[]
 for c in fixture['cases']:
  argv=[a.executable]+([str(c['old']),str(c['new'])] if KIND==1 else []);result=run(argv);commands.append({'argv':argv,'returncode':0,'stdout':result})
  if KIND==1:expected=[str(c['slot'])]+[' '.join(map(str,row)) for row in c['observers']]
  elif KIND in [4,5]:expected=['1 1 '+str(int(c['deleted']))]
  else:expected=['%s %s %s %.9g %.9g %.9g'%(x['type'],x['tag'],x['name'],x['values'][0],x['values'][1],x['values'][3]) for x in c['descriptors']]
  assert result.splitlines()==expected,(result,expected)
 if KIND>=17:
  argv=[a.executable,'failures'];result=run(argv);commands.append({'argv':argv,'returncode':0,'stdout':result,'domain':'Real CCL allocation exceptions; no original exception equivalence claim'})
 summary={'version':1,'cpp_differential_passed':True,'cases':len(fixture['cases']),'target':TARGET,'functions':[{'original_elf_sha256':TARGET['original_elf_sha256'],'mangled':TARGET['mangled'],'domain':'Original application normal-path instruction trace and real pinned CCL provider behavior in initialized source-port state'}],'commands':commands,'native_range':{k:fixture[k] for k in ['elf_sha256','section','file_offset','range_sha256']},'limitations':fixture['limitations']}
 if a.proof_out:
  out=Path(a.proof_out);assert not out.exists(),'Proof output must be new';run([CANON/'uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*SOURCES]);text=run(['/usr/bin/nm','--defined-only',a.executable]);assert TARGET['mangled'] in {l.split()[-1] for l in text.splitlines() if l.split()}
  summary.update(produced_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),compiled_mangled_names_matched=True,source_bindings={str(Path(x).relative_to(ROOT) if Path(x).is_absolute() else x):sha(x) for x in SOURCES},repository_sources={'third_party/ccl-framework/core/portable/'+x:sha(ROOT/'third_party/ccl-framework/core/portable'/x) for x in PROVIDERS},producer_hashes={'check.py':sha(HERE/'check.py'),'native.py':sha(HERE/'native.py')},fixture={'path':a.fixtures,'sha256':sha(a.fixtures)},executable={'path':a.executable,'sha256':sha(a.executable)},formatter_version=subprocess.check_output([CANON/'uc-library/.venv/bin/clang-format','--version'],text=True).strip())
  summary['objects']=[{'path':x,'sha256':sha(x)} for x in a.object]
  if a.integration_proof:summary['integration_proof']={'path':a.integration_proof,'sha256':sha(a.integration_proof)}
  out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(summary,indent=2)+'\n')
 print(json.dumps({'passed':True,'cases':len(fixture['cases'])}))
if __name__=='__main__':main()
