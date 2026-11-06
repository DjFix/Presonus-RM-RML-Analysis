"""Real pinned CCL compile and independent ARM/portable differential replay."""
import json,os,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[4];T=Path(__file__).resolve().parent
OUT=R/'temp/recovery-work/rolling200-03/focus01-local';OUT.mkdir(parents=True,exist_ok=True)
EXE=OUT/'replay'
OWNED=['uc-library/include/presonus/FocusHelperButton.hpp','uc-library/src/Presonus/FocusHelperButton.cpp','uc-library/tests/recovery/FocusHelperInputReplay.cpp']
LIB='temp/core-upstream/root-integration-01/upstream-core/sdk/lib/'
COMPILE=['/usr/bin/c++','-std=c++17','-O0','-fno-rtti','-fno-lto','-Wno-multichar','-ffunction-sections','-fdata-sections','-fno-fast-math','-Iuc-library/include','-Ithird_party/ccl-framework',*OWNED[1:],'temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a',LIB+'libcorelib.a',LIB+'libpresonus_core_allocator.a','-Wl,--gc-sections','/usr/lib/x86_64-linux-gnu/libpng16.so.16','-lz','-lpthread','-ldl','-lm','-o',str(EXE)]
def run(argv,**kw):
 print(json.dumps(list(map(str,argv))),flush=True)
 p=subprocess.run(list(map(str,argv)),cwd=R,text=True,capture_output=True,env={**os.environ,'TMPDIR':str(OUT)},**kw)
 if p.returncode:print(p.stdout+p.stderr);p.check_returncode()
 return p
if __name__=='__main__':
 mode=sys.argv[1]
 if mode=='format':print(run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*OWNED]).stdout)
 elif mode=='compile':print(run(COMPILE).stdout)
 elif mode=='symbols':
  import native
  symbols={x.split()[-1] for x in run(['/usr/bin/nm','--defined-only',EXE]).stdout.splitlines() if x.split()}
  for n in native.NAMES[:4]:assert n in symbols,n;print(n)
 elif mode=='native':
  import native
  assert native.generate()==json.loads((T/'fixtures.json').read_text());print('Fresh bounded native instruction executions reproduce fixtures')
 elif mode=='replay':
  cases=json.loads((Path(sys.argv[3]) if len(sys.argv)>3 else T/'fixtures.json').read_text())['cases']
  exe=Path(sys.argv[2]) if len(sys.argv)>2 else EXE
  text=''
  for c in cases:
   mode,bits,value,active,msg,parent,root,names=c['input'];text+=' '.join(map(str,[mode,bits,value,active,msg,parent,root,len(names),*names]))+'\n'
  p=run([exe],input=text);lines=p.stdout.splitlines();assert len(lines)==len(cases),(len(lines),len(cases),p.stderr)
  for j,(line,c) in enumerate(zip(lines,cases)):assert list(map(int,line.split()))==c['expected'],(j,c,line)
  print(len(cases),'native differential cases and real CCL constructor/attributes/notifications/focus/drawing regressions')
 else:raise SystemExit(mode)
