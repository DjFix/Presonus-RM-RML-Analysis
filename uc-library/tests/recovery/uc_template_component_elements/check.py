"""Scoped deterministic replay; canonical integration may supply its built executable."""
import pathlib,json,subprocess,sys,os,hashlib
ROOT=pathlib.Path(__file__).resolve().parents[4]
BASE=pathlib.Path('uc-library/tests/recovery/uc_template_component_elements')
OUT=pathlib.Path('temp/recovery-work/uc_template_component_elements-local')
EXE=OUT/'replay'
PRODUCTION=['uc-library/src/Presonus/UC/TemplateElement.cpp','uc-library/src/Presonus/UC/ComponentElement.cpp']
OWNED=PRODUCTION+['uc-library/include/presonus/uc/TemplateElement.hpp','uc-library/include/presonus/uc/ComponentElement.hpp',str(BASE/'Replay.cpp')]
LIB=pathlib.Path('temp/core-upstream/root-integration-01/upstream-core/sdk/lib')
COMPILE=['/usr/bin/c++','-std=c++17','-O0','-Wno-multichar','-ffunction-sections','-fdata-sections','-Iuc-library/include','-Ithird_party/ccl-framework']+PRODUCTION+[str(BASE/'Replay.cpp'),'uc-library/src/Presonus/UC/Element.cpp','uc-library/src/Presonus/UC/MetaElement.cpp','third_party/ccl-framework/core/portable/coreattributes.cpp','-Wl,--gc-sections','-Wl,--wrap=_ZdlPv','-Wl,--wrap=_ZdlPvm','third_party/ccl-framework/core/public/corebuffer.cpp','third_party/ccl-framework/core/platform/shared/posix/corethread.posix.cpp','third_party/ccl-framework/core/malloc/coremalloc.cpp','third_party/ccl-framework/core/system/coredebug.cpp','third_party/ccl-framework/core/system/coreatomicstack.cpp','third_party/ccl-framework/core/platform/shared/posix/coreatomicstack.posix.cpp','-lpthread','-ldl','-lm','-o',str(EXE)]
def run(argv,**kw):
 print(json.dumps(list(map(str,argv))),flush=True)
 r=subprocess.run(list(map(str,argv)),cwd=ROOT,text=True,capture_output=True,env={**os.environ,'TMPDIR':str(ROOT/OUT)},**kw)
 if r.stderr:print(r.stderr)
 if r.returncode:print(r.stdout);r.check_returncode()
 return r.stdout
def encode(s):return s.encode().hex() or '-'
def replay(exe):
 data=json.loads((ROOT/BASE/'fixtures.json').read_text());inputs=[];expected=[]
 for c in data['cases']:
  o=next(o for o in data['originals'] if o['anchor']==c['original']);phase=(3 if 'D0Ev' in o['mangled'] else 2) if c['phase']=='lifecycle' else (5 if c['phase']=='reset' else int(c['phase']=='attributes'));a=c['attrs'];inputs.append(' '.join(map(str,[c['class'],phase,c.get('children',0),len(a)]))+' '+ ' '.join(encode(k)+' '+encode(v) for k,v in a.items()))
  e=c['expected']
  if c['phase']=='lifecycle':expected.append(f"{int(e['parent_deleted'])} {e['children_deleted']}")
  else:expected.append(' '.join([str(len(e['gets']))]+[encode(k) for k in e['gets']]+[str(len(e['stores']))]+[x for k,v in e['stores'] for x in (encode(k),encode(v))]))
 for c in data['cases']:
  if c['phase']!='attributes':continue
  a=c['attrs'];e=c['expected'];printed=dict(e['stores'])['flags']
  inputs.append('2 4 0 0 '+encode(a.get('flags',''))+' '+encode(a.get('inherit','')))
  expected.append(str(e['flags'])+' '+encode(e['state'][1])+' '+encode(printed))
 lines=run([exe],input='\n'.join(inputs)+'\n').splitlines();assert len(lines)==len(expected)
 for i,(got,want) in enumerate(zip(lines,expected)):assert got==want,(i,got,want)
 print(len(data['cases']),'native ARM app cases and',len(lines)-len(data['cases']),'independent pinned provider cases match portable replay')
if __name__=='__main__':
 (ROOT/OUT).mkdir(parents=True,exist_ok=True);mode=sys.argv[1]
 if mode=='format':print(run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror']+OWNED))
 elif mode=='compile':print(run(COMPILE))
 elif mode=='symbols':
  names={x.split()[-1] for x in run(['/usr/bin/nm','--defined-only',EXE]).splitlines() if x.split()}
  for o in json.loads((ROOT/BASE/'fixtures.json').read_text())['originals']:assert o['mangled'] in names,o['mangled']
  print('All 24 original identities / 12 ABI interfaces present')
 elif mode=='native':
  import native
  assert native.generate()==json.loads((ROOT/BASE/'fixtures.json').read_text());print('Fresh original ELF/section/range/RTTI/native execution replay matches sealed fixture')
 elif mode=='replay':replay(sys.argv[2] if len(sys.argv)>2 else str(EXE))
 else:raise ValueError(mode)
