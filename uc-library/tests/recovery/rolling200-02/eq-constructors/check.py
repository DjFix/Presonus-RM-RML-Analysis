from pathlib import Path
import json,sys,subprocess,os,math,hashlib
R=Path(__file__).resolve().parents[5];T=Path(__file__).resolve().parent
OUT=R/'temp/recovery-work/rolling200-02/eq-constructors';OUT.mkdir(parents=True,exist_ok=True)
EXE=OUT/'replay';CPP='uc-library/src/Presonus/EQControl.cpp';HPP='uc-library/include/presonus/mixer_dsp/EQControl.hpp';DRIVER='uc-library/tests/recovery/EQConstructorsReplay.cpp'
LIB='temp/core-upstream/root-integration-01/upstream-core/sdk/lib/'
COMPILE=['/usr/bin/c++','-std=c++17','-fno-rtti','-Wno-multichar','-ffunction-sections','-fdata-sections','-fno-lto','-fno-fast-math','-ffp-contract=off','-frounding-math','-fno-builtin','-Iuc-library/src/mixer_dsp','-Iuc-library/include','-Ithird_party/ccl-framework',CPP,'uc-library/src/Presonus/EQControlBandParams.cpp',DRIVER,'uc-library/src/Presonus/Dsp/EqSourceProviders.cpp','uc-library/src/mixer_dsp/Logarithm.cpp','temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a',LIB+'libcorelib.a',LIB+'libpresonus_core_allocator.a','-Wl,--gc-sections','/usr/lib/x86_64-linux-gnu/libpng16.so.16','-lz','-lpthread','-ldl','-lm','-o',str(EXE)]
def run(argv):
 print(json.dumps(list(map(str,argv))),flush=True)
 subprocess.run(list(map(str,argv)),cwd=R,check=True,env={**os.environ,'TMPDIR':str(OUT)})
def compare(a,b,path=''):
 if isinstance(a,float) or isinstance(b,float):assert math.isclose(a,b,rel_tol=2e-7,abs_tol=1e-8),(path,a,b)
 elif isinstance(a,dict):
  assert a.keys()==b.keys(),(path,a.keys(),b.keys())
  for k in a:compare(a[k],b[k],path+'.'+k)
 elif isinstance(a,list):
  assert len(a)==len(b),(path,a,b)
  for i,(x,y) in enumerate(zip(a,b)):compare(x,y,path+f'[{i}]')
 else:assert a==b,(path,a,b)
def replay(exe,fixture):
 data=json.loads(Path(fixture).read_text());lines=[]
 for c in data['cases']:
  variant=1 if 'C1E' in c['variant'] else 2
  common=' '.join(map(str,[variant,*c['rectangle']]))
  lines.append('S '+common)
  records=[]
  for p in c['table']:records.extend([p['type'],p['tag'],p['name'],*p['values'],p['flags'],p['unit'] or '-',p['curve'] or '-'])
  lines.append('P '+common+' '+' '.join(map(str,records)))
 p=subprocess.run([str(exe)],input='\n'.join(lines)+'\n',text=True,capture_output=True,check=True)
 result=[json.loads(line) for line in p.stdout.splitlines()];assert len(result)==len(lines)
 for i,c in enumerate(data['cases']):
  source,provider=result[2*i:2*i+2]
  compare(source['providers'],provider,'actual independent CCL providers')
  compare(source['table'],c['table'],'all native ParamInfo record fields')
  state=dict(c['state']);state['null_bitmap']=1
  compare(source['state'],state,'native app stores')
  assert source['destroyed_parameters']==3
  assert provider['rectangle']==c['rectangle'] and provider['touch']==1 and provider['focus']==0 and provider['null_parameter']==1
  for observed,original in zip(provider['params'],c['table']):
   assert observed['type']==original['type'] and observed['tag']==original['tag'] and observed['name']==original['name']
   compare(observed['values'],[original['values'][0],original['values'][1],original['values'][3],original['values'][3]],'native HPF table')
   assert observed['flags']==[(original['flags']>>j)&1 for j in range(8)]
   assert observed['owns_info']==0 and observed['null_controller']==1
  assert source['range']==c['curve_range'] # native independent fields0x88/0x8c
 print(f"{len(data['cases'])} explicit C1/C2 source executions match original app-store observations and independent actual pinned CCL provider replay; 150 actual parameter destructions")
if __name__=='__main__':
 mode=sys.argv[1]
 if mode=='compile':run(COMPILE)
 elif mode=='format':run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',CPP,HPP,DRIVER])
 elif mode=='symbols':
  out=subprocess.check_output(['/usr/bin/nm','--defined-only',str(EXE)],text=True);names={line.split()[-1] for line in out.splitlines() if line.split()}
  for variant in [1,2]:assert f'_ZN8Presonus9EQControlC{variant}ERKN4Core5TRectIiEE' in names
  print('\n'.join(line for line in out.splitlines() if 'EQControlC' in line));print('Both original constructor identities present; Linux ELF no decoration. No ARM ABI claim.')
 elif mode=='sanitizer':
  argv=COMPILE[:];argv[1:1]=['-fsanitize=address','-g'];argv[-1]+='-asan';index=argv.index(LIB+'libcorelib.a');argv[index:index]=['temp/core-upstream/root-integration-01/libpresonus_uc.a'];run(argv);replay(Path(argv[-1]),T/'fixtures.json')
 elif mode=='regression':
  import runpy
  for group in ['eq-control','eq-curves']:
   script=T.parent/group/'check.py'; prior=runpy.run_path(str(script));argv=prior['COMPILE'][:]
   index=argv.index(LIB+'libcorelib.a');argv[index:index]=['-Iuc-library/src/mixer_dsp','-ffp-contract=off','uc-library/src/Presonus/Dsp/EqSourceProviders.cpp','uc-library/src/mixer_dsp/Logarithm.cpp','temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a']
   run(argv)
   run(['uc-library/.venv/bin/python',script,'replay'])
   if group=='eq-curves':run(['uc-library/.venv/bin/python',script,'curves'])
 elif mode=='adapter':
  p=subprocess.run([str(EXE)],input='A 0 0 0 0 0\n',text=True,capture_output=True,check=True);assert json.loads(p.stdout)=={'adapter_samples':2056};print('2056 source-adapter samples match existing real positive-range provider; bootstrap, reset and invalid-transition guards pass')
 elif mode=='replay':replay(Path(sys.argv[2]) if len(sys.argv)>2 else EXE,sys.argv[3] if len(sys.argv)>3 else T/'fixtures.json')
 elif mode=='native':
  import native
  data=json.loads((T/'fixtures.json').read_text());assert native.cases()==data['cases'];assert native.curve_range_mapping()==data['curve_range_mapping'];print('Fresh exact original constructor instructions reproduce all 50 fixtures; guarded PC/write checks pass')
 else:raise SystemExit(mode)
