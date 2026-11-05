import pathlib,sys,subprocess,json,os,hashlib
ROOT=pathlib.Path(__file__).resolve().parents[5]
TEST=pathlib.Path(__file__).resolve().parent
OUT=ROOT/'temp/recovery-work/rolling200-02/eq-control';OUT.mkdir(parents=True,exist_ok=True)
EXE=OUT/'driver'
CPP='uc-library/src/Presonus/EQControl.cpp';HEADER='uc-library/include/presonus/mixer_dsp/EQControl.hpp'
FILES=[CPP,HEADER,str((TEST/'driver.cpp').relative_to(ROOT))]
LIB='temp/core-upstream/root-integration-01/upstream-core/sdk/lib/'
COMPILE=['/usr/bin/c++','-std=c++17','-fno-rtti','-Wno-multichar','-ffunction-sections','-fdata-sections','-Iuc-library/include','-Ithird_party/ccl-framework',CPP,'uc-library/src/Presonus/EQControlBandParams.cpp',str(TEST/'driver.cpp'),LIB+'libcorelib.a',LIB+'libpresonus_core_allocator.a','-Wl,--gc-sections','/usr/lib/x86_64-linux-gnu/libpng16.so.16','-lz','-lpthread','-ldl','-o',str(EXE)]
def run(argv):
 print(json.dumps(argv),flush=True);subprocess.run(argv,cwd=ROOT,check=True,env={**os.environ,'TMPDIR':str(OUT)})
def replay(exe,fixtures):
 data=json.load(open(fixtures));lines=[]
 for c in data['cases']:
  t=c['target'];count=c.get('count',0)
  fields=[t,count,c.get('index',0),int(c.get('buffered',c.get('present',False))),c.get('value',0),c.get('minimum',0),int(c.get('primary',bool(c.get('bands',[[0,0,0,1]])[0][3]) if t==3 else True)),c.get('repeats',c.get('kind',0)),c.get('x',0),c.get('y',0),c.get('width',100),c.get('height',80)]
  bands=c.get('bands',[[0,0,0]]*count)
  for i,b in enumerate(bands):fields+=b[:3]+[int(c['enabled_parameters'][i]) if t==1 else int(c.get('buffered',c.get('present',False)))]
  if t==3:fields+=c['clip']+c['samples']
  if t==2:fields+=[c['message']]+[x for band in c['slots'] for x in band]
  lines.append(' '.join(map(str,fields)))
 result=subprocess.run([str(exe)],input='\n'.join(lines)+'\n',text=True,capture_output=True,check=True)
 observed=result.stdout.splitlines();assert len(observed)==len(lines),(len(observed),len(lines),result.stderr)
 for i,(c,line) in enumerate(zip(data['cases'],observed)):
  parts=line.split();exp=c['expected'];expected=[]
  if c['target']==2:
   vals=[x for band in exp['slots'] for x in band]+exp['dirty']+exp['enabled']+[int(not any(call[0]=='remove-observer' for call in exp['calls']))]
   assert list(map(int,parts))==vals,(i,c,line,vals)
   continue
  if c['target']==4:
   vals=[exp['band_count'],exp['parameter_count'],exp['buffer_present'],exp['buffer_valid']]+exp['dirty']+exp['enabled']+exp['band_curve_sizes']+[int(exp['amplitude_zero']),int(exp['pixel_zero'])]
   assert list(map(int,parts))==vals,(i,c,line,vals)
   continue
  if c['target']==3:
   vals=[':'.join(map(str,x)) for x in exp['lines']]
   assert int(parts[0])==len(vals) and parts[1:]==vals,(i,c,line)
   continue
  for call in exp['calls']:expected.append(':'.join(map(str,call)))
  assert int(parts[0])==exp['result'] and int(parts[1])==len(expected) and parts[2:]==expected,(i,c,line)
 print(f"{len(lines)} cases match independently executed ARM results and parameter call traces")
def symbols():
 out=subprocess.check_output(['/usr/bin/nm','--defined-only',str(EXE)],text=True);names={x.split()[-1] for x in out.splitlines() if x.split()}
 for t in [1,2,3,4,5,6,7,8,9]:
  req=json.load(open(ROOT/f'temp/recovery-work/rolling200-02/implementation-plan01/packets-batch03/packets/rolling200_02_impl_w04_{t:02}/request.json'))
  name=req['targets'][0]['mangled'];assert name in names,name;print(name)
 print('9 exact manglings; host Linux ELF has no decoration. No ARM ABI claim.')
if __name__=='__main__':
 mode=sys.argv[1]
 if mode=='format':run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror']+FILES)
 elif mode=='compile':run(COMPILE)
 elif mode=='symbols':symbols()
 elif mode=='replay':replay(pathlib.Path(sys.argv[2]) if len(sys.argv)>2 else EXE,sys.argv[3] if len(sys.argv)>3 else TEST/'fixtures.json')
 elif mode=='native':
  import importlib.util
  spec=importlib.util.spec_from_file_location('oracle',TEST/'native.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
  assert mod.cases()==json.load(open(TEST/'fixtures.json'))['cases'];mod.write_audit(OUT/'native-pc-audit-replay.json');print('Fresh ARM executions reproduce all fixtures; fail-closed executed-PC audit passed')
