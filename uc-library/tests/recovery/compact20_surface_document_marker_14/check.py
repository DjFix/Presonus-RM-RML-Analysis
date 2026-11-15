import json,os,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[4];T=Path(__file__).resolve().parent
OUT=R/'temp/recovery-work/marker14';OUT.mkdir(parents=True,exist_ok=True)
EXE=OUT/'replay';OBJ=OUT/'production.o';DRIVER=OUT/'driver.o';LIBS=R/'temp/provider-baseline08'
OWNED=['uc-library/include/presonus/surface/MarkerPageComponent.hpp','uc-library/src/Presonus/Surface/MarkerPageComponent.cpp',str(T.relative_to(R)/'Replay.cpp')]
FLAGS=['/usr/bin/c++','-std=c++20','-fno-rtti','-fno-lto','-Wno-multichar','-ffunction-sections','-fdata-sections','-UNDEBUG','-Iuc-library/include','-Ithird_party/ccl-framework']
COMPILE=[[*FLAGS,'-O3','-c',OWNED[1],'-o',str(OBJ)],[*FLAGS,'-O0','-c',OWNED[2],'-o',str(DRIVER)],['/usr/bin/c++',str(OBJ),str(DRIVER),'-Wl,--gc-sections',str(LIBS/'libcorelib.a'),str(LIBS/'libpresonus_core_allocator.a'),'-lz','-lpthread','-ldl','-lm','-o',str(EXE)]]
def run(argv,**kw):
 argv=list(map(str,argv));print(json.dumps(argv),flush=True);p=subprocess.run(argv,cwd=R,capture_output=True,env={**os.environ,'TMPDIR':str(OUT)},**kw)
 if p.returncode:print(p.stdout.decode(),p.stderr.decode());p.check_returncode()
 return p
if __name__=='__main__':
 mode=sys.argv[1]
 if mode=='format':run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*OWNED])
 elif mode=='compile':
  for argv in COMPILE:run(argv)
 elif mode=='symbols':
  import native
  symbols={x.split()[-1] for x in run(['/usr/bin/nm','--defined-only',OBJ]).stdout.decode().splitlines() if x.split()};assert native.NAME in symbols;print(native.NAME)
 elif mode=='native':
  import native
  assert native.generate(EXE)==json.loads((T/'fixtures.json').read_text());print('Independent original ARM replay reproduces all fixtures')
 elif mode=='replay':
  exe=Path(sys.argv[2]) if len(sys.argv)>2 else EXE;fixture=Path(sys.argv[3]) if len(sys.argv)>3 else T/'fixtures.json';cases=json.loads(fixture.read_text())['cases'];payload=''.join(' '.join(map(str,c['input']))+'\n' for c in cases).encode()
  values=run([exe],input=payload).stdout.decode().splitlines();assert len(values)==len(cases)
  for case,value in zip(cases,values):assert int(value)==case['expected'],(case,value)
  print(len(cases),'original ARM app differential cases passed; actual CCL provider observations; float runtime intercept excludes helper equivalence')
 elif mode=='proof':
  import hashlib,datetime,native
  exe=Path(sys.argv[2]).resolve();fixture=Path(sys.argv[3]).resolve();output=Path(sys.argv[4]);assert not output.exists()
  run([sys.executable,__file__,'replay',exe,fixture])
  assert native.generate(exe)==json.loads(fixture.read_text())
  output.parent.mkdir(parents=True,exist_ok=True)
  hashes={p:hashlib.sha256((R/p).read_bytes()).hexdigest() for p in OWNED+[str(T.relative_to(R)/'native.py'),str(T.relative_to(R)/'check.py')]}
  output.write_text(json.dumps({'version':1,'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'arm_differential_passed':True,'functions':[{'original_elf_sha256':native.SHA,'mangled':native.NAME,'domain':json.loads(fixture.read_text())['scope'],'cases':13}],'source_producer_hashes':hashes,'fixture_sha256':hashlib.sha256(fixture.read_bytes()).hexdigest(),'executable_sha256':hashlib.sha256(exe.read_bytes()).hexdigest()},indent=2)+'\n')
 else:raise SystemExit(mode)
