import json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[4];T=Path(__file__).resolve().parent;MODE='text'
OUT=R/'temp/mackie'/MODE;OUT.mkdir(parents=True,exist_ok=True);EXE=OUT/'replay'
SOURCES=['uc-library/src/Presonus/MackieControlComponent.cpp',str(T.relative_to(R)/'Replay.cpp')]
OWNED=['uc-library/include/presonus/MackieControlComponent.hpp',*SOURCES]
COMPILE=['/usr/bin/c++','-std=c++17','-O0','-fno-rtti','-fno-lto','-Wno-multichar','-ffunction-sections','-fdata-sections','-Iuc-library/include','-Ithird_party/ccl-framework',*SOURCES,'temp/mackie/links/libpresonus_private_glibc29.a','temp/mackie/links/libcorelib.a','temp/mackie/links/libpresonus_core_allocator.a','-Wl,--gc-sections','/usr/lib/x86_64-linux-gnu/libpng16.so.16','-lz','-lpthread','-ldl','-lm','-o',str(EXE)]
def run(argv,**kw):
 print(json.dumps(list(map(str,argv))),flush=True);p=subprocess.run(list(map(str,argv)),cwd=R,text=True,capture_output=True,**kw)
 if p.returncode:print(p.stdout+p.stderr);p.check_returncode()
 return p
if __name__=='__main__':
 mode=sys.argv[1]
 if mode=='compile':run(COMPILE)
 elif mode=='format':run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*OWNED])
 elif mode=='symbols':
  import native
  assert native.NAME in {x.split()[-1] for x in run(['nm','--defined-only',EXE]).stdout.splitlines() if x.split()}
 elif mode=='native':
  import native
  assert native.generate()==json.loads((T/'fixtures.json').read_text())
 elif mode=='replay':
  fixture=Path(sys.argv[3]) if len(sys.argv)>3 else T/'fixtures.json';cases=json.loads(fixture.read_text())['cases'];exe=Path(sys.argv[2]) if len(sys.argv)>2 else EXE
  result=run([exe],input=''.join(' '.join(map(str,c['input']))+'\n' for c in cases)).stdout.splitlines();assert len(result)==len(cases)
  for c,line in zip(cases,result):
   present,state,unused,text=c['input'];call=c['trace'][1] if present else None
   expectedValue=(str(int(call[1]!=0)) if present else '0') if MODE=='led' else (call[1] or '~') if present else '~'
   changed=int(present and (state!=0 if MODE=='led' else text!='~'))
   assert line.split()==[expectedValue,str(changed),'0',str(changed),'0'],(c,line)
  print(len(cases),'native dispatch / actual CCL value and notification cases')
 else:raise SystemExit(mode)
