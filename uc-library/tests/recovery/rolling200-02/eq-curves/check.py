from pathlib import Path
import sys,subprocess,json,os,datetime
ROOT=Path(__file__).resolve().parents[5];TEST=Path(__file__).resolve().parent
OUT=ROOT/'temp/recovery-work/rolling200-02/eq-curves';OUT.mkdir(parents=True,exist_ok=True)
EXE=OUT/'driver';CPP='uc-library/src/Presonus/EQControl.cpp';HEADER='uc-library/include/presonus/mixer_dsp/EQControl.hpp'
FILES=[CPP,HEADER,str((TEST/'driver.cpp').relative_to(ROOT))]
LIB='temp/core-upstream/root-integration-01/upstream-core/sdk/lib/'
COMPILE=['/usr/bin/c++','-std=c++17','-fno-rtti','-Wno-multichar','-ffp-contract=off','-ffunction-sections','-fdata-sections','-Iuc-library/include','-Ithird_party/ccl-framework',CPP,'uc-library/src/Presonus/EQControlBandParams.cpp','uc-library/src/DSP/BiquadMethods.cpp','uc-library/src/DSP/BiquadIncremental.cpp','uc-library/src/DSP/BiquadSine.cpp',str(TEST/'driver.cpp'),LIB+'libcorelib.a',LIB+'libpresonus_core_allocator.a','-Wl,--gc-sections','-Wl,--wrap=clock_gettime','/usr/lib/x86_64-linux-gnu/libpng16.so.16','-lz','-lpthread','-ldl','-lm','-o',str(EXE)]
LOG=ROOT/'evidence/recovery/2026-11-05/rolling200-02/eq-curves/checks'
LOG.mkdir(parents=True,exist_ok=True)
def run(argv):
 argv=list(map(str,argv));mode=sys.argv[1]
 p=subprocess.run(argv,cwd=ROOT,text=True,capture_output=True,env={**os.environ,'TMPDIR':str(OUT)})
 (LOG/(mode+'.stdout')).write_text(p.stdout);(LOG/(mode+'.stderr')).write_text(p.stderr)
 (LOG/(mode+'.json')).write_text(json.dumps({'argv':argv,'returncode':p.returncode,'finished':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2)+'\n')
 assert p.returncode==0,(argv,p.stderr[-6000:]);return p.stdout
if __name__=='__main__':
 mode=sys.argv[1]
 if mode=='compile':run(COMPILE)
 elif mode=='format':run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*FILES])
 elif mode=='symbols':
  text=run(['/usr/bin/nm','--defined-only',EXE]);names={x.split()[-1] for x in text.splitlines() if x.split()}
  for i in range(1,6):
   r=json.loads((ROOT/f'temp/recovery-work/rolling200-02/implementation-plan01/packets-current-eq01/packets/rolling200_02_current_eq_{i:02d}/request.json').read_text());assert r['targets'][0]['mangled'] in names
 elif mode=='curves':run(['uc-library/.venv/bin/python',TEST/'replay_curves.py',EXE,TEST/'curve-fixtures.json'])
 elif mode=='replay':
  fixtures=json.loads((TEST/'fixtures.json').read_text());lines=[]
  for c in fixtures['cases']:
   t=c['target']
   fields=[t]+([c['count']] if t==1 else c['rectangle'] if t==2 else [c['last'],c['now_ns']])
   lines.append(' '.join(map(str,fields)))
  p=subprocess.run([str(EXE)],input='\n'.join(lines)+'\n',text=True,capture_output=True,check=True);out=p.stdout.splitlines();assert len(out)==len(lines)
  for c,line in zip(fixtures['cases'],out):
   vals=list(map(int,line.split()));t=c['target'];exp=c['expected']
   if t==1:assert vals==[exp['count'],exp['count'],exp['count'],8]+[1]*exp['count']
   elif t==2:
    rect=exp['trace'][0]['rectangle'];width=rect[2]-rect[0];height=rect[3]-rect[1];assert vals==rect+[width if width>0 and height>0 else 0],(c,vals)
   else:assert vals==[exp['last'],c['now_ns'],0 if any(x['call']=='rebuildCurves' for x in exp['trace']) else 1],(c,vals)
  print(f'{len(lines)} original ARM cases match actual CCL-backed EQ entries')
 elif mode=='native':
  import native
  assert native.cases()==json.loads((TEST/'fixtures.json').read_text())['cases'];print('Fresh original executions reproduce all boundary fixtures')
 else:raise SystemExit(mode)
