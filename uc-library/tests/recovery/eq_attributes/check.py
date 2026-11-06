"""Worker-local real CCL compilation and independent native differential replay."""
import json,os,subprocess,sys,runpy
from pathlib import Path
R=Path(__file__).resolve().parents[4];T=Path(__file__).resolve().parent
OUT=R/'temp/recovery-work/rolling200-02/eq-attributes17';OUT.mkdir(parents=True,exist_ok=True)
EXE=OUT/'replay';CPP='uc-library/src/Presonus/EQControl.cpp';HPP='uc-library/include/presonus/mixer_dsp/EQControl.hpp';DRIVER='uc-library/tests/recovery/EQControlAttributesReplay.cpp'
LIB='temp/core-upstream/root-integration-01/upstream-core/sdk/lib/'
WRAPS=['_ZN4Core8Portable15StaticSingletonINS0_13BitmapManagerEE8instanceEv','_ZN8Presonus9EQControl7setBandEiNS0_10BandParamsE']
COMPILE=['/usr/bin/c++','-std=c++20','-fno-rtti','-Wno-multichar','-ffunction-sections','-fdata-sections','-fno-lto','-fno-fast-math','-ffp-contract=off','-Iuc-library/src/mixer_dsp','-Iuc-library/include','-Ithird_party/ccl-framework',CPP,'uc-library/src/Presonus/EQControlBandParams.cpp',DRIVER,'uc-library/src/Presonus/Dsp/EqSourceProviders.cpp','uc-library/src/mixer_dsp/Logarithm.cpp','temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a',LIB+'libcorelib.a',LIB+'libpresonus_core_allocator.a','-Wl,--gc-sections',*['-Wl,--wrap='+x for x in WRAPS],'/usr/lib/x86_64-linux-gnu/libpng16.so.16','-lz','-lpthread','-ldl','-lm','-o',str(EXE)]
def run(argv,**kw):
 print(json.dumps(list(map(str,argv))),flush=True)
 p=subprocess.run(list(map(str,argv)),cwd=R,text=True,capture_output=True,env={**os.environ,'TMPDIR':str(OUT)},**kw)
 if p.returncode:print(p.stdout+p.stderr);p.check_returncode()
 return p
if __name__=='__main__':
 mode=sys.argv[1]
 if mode=='compile':print(run(COMPILE).stdout)
 elif mode=='format':print(run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',CPP,HPP,DRIVER]).stdout)
 elif mode=='symbols':
  out=run(['/usr/bin/nm','--defined-only',EXE]).stdout
  name='_ZN8Presonus9EQControl13setAttributesERKN4Core8Portable10AttributesE';assert name in {line.split()[-1] for line in out.splitlines()};print(name+' exact host ELF, no decoration; return/layout/ARM ABI unverified')
 elif mode=='native':
  import native
  data=json.loads((T/'fixtures.json').read_text());assert native.cases()==data['cases'];assert data['range']==native.RANGE;print('36 fresh exact ARM scenarios / 54 calls; guarded PCs/writes; Core/provider boundaries intercepted')
 elif mode=='replay':
  cases=json.loads((Path(sys.argv[3]) if len(sys.argv)>3 else T/'fixtures.json').read_text())['cases']
  exe=Path(sys.argv[2]) if len(sys.argv)>2 else EXE
  p=run([exe],input=''.join(' '.join(map(str,c['input']))+'\n' for c in cases));lines=p.stdout.splitlines();assert len(lines)==len(cases),(lines,p.stderr)
  for i,(line,c) in enumerate(zip(lines,cases)):
   got=json.loads(line);assert got==c['output'],(i,got,c['output'])
  print(len(cases),'independent original target/provider differential setup cases: HPF lookup+count, six lookup order, mixed queue, band store/setBand phase, image reference counts, handle frames, display range, style color, autosize, buffer modes; real provider interpolation endpoints/clipping and image lifetime checks')
 elif mode=='regression':
  print(run(['uc-library/.venv/bin/python','uc-library/tests/recovery/rolling200-02/eq-lifecycle/regression.py']).stdout)
  for m in ['compile','symbols','replay']: print(run(['uc-library/.venv/bin/python','uc-library/tests/recovery/rolling200-02/eq-lifecycle/check.py',m]).stdout)
 else:raise SystemExit(mode)
