import pathlib,sys,subprocess,json,os
ROOT=pathlib.Path(__file__).resolve().parents[5];TEST=pathlib.Path(__file__).parent
OUT=ROOT/'temp/recovery-work/rolling200-02/pan-drawing';EXE=OUT/'driver'
FILES=['uc-library/include/presonus/PanControl.hpp','uc-library/src/Presonus/PanControl.cpp',str((TEST/'driver.cpp').relative_to(ROOT))]
LIB='temp/core-upstream/root-integration-01/upstream-core/sdk/lib/'
CMD=['/usr/bin/c++','-std=c++17','-fno-rtti','-Wno-multichar','-ffunction-sections','-fdata-sections','-Iuc-library/include','-Ithird_party/ccl-framework','uc-library/src/Presonus/PanControl.cpp','uc-library/src/Presonus/PanControlBindings.cpp',str(TEST/'driver.cpp'),LIB+'libcorelib.a',LIB+'libpresonus_core_allocator.a','-Wl,--gc-sections','/usr/lib/x86_64-linux-gnu/libpng16.so.16','-lz','-lpthread','-ldl','-o',str(EXE)]
def run(cmd):print(json.dumps(cmd),flush=True);subprocess.run(cmd,cwd=ROOT,check=True,env={**os.environ,'TMPDIR':str(OUT)})
def replay(exe,fixture):
 cases=json.load(open(fixture))['cases'];keys=['target','width','height','mark','stereo','link','side','aux','primary','image','enabled','bw','bh','frames','value','other']
 data='\n'.join(' '.join(str(c[k]) for k in keys) for c in cases)+'\n'
 p=subprocess.run([str(exe)],input=data,text=True,capture_output=True,check=True);lines=p.stdout.splitlines();assert len(lines)==len(cases),(len(lines),len(cases),p.stderr)
 for i,(c,line) in enumerate(zip(cases,lines)):
  expected=[':'.join(map(str,x)) for x in c['expected']];words=line.split();assert int(words[0])==len(expected) and words[1:]==expected,(i,c,line,expected)
 print(len(cases),'portable executions match independently observed native drawing call geometry and colors; actual CCL rendering invoked')
if __name__=='__main__':
 mode=sys.argv[1]
 if mode=='format':run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror']+FILES)
 elif mode=='compile':run(CMD)
 elif mode=='symbols':
  names={x.split()[-1] for x in subprocess.check_output(['/usr/bin/nm','--defined-only',str(EXE)],text=True).splitlines() if x.split()}
  for n in ['13drawValueMark','15drawImagePanner']:
   name='_ZN8Presonus10PanControl'+n+'ERKN4Core8Portable9DrawEventE';assert name in names,name;print(name)
 elif mode=='replay':replay(pathlib.Path(sys.argv[2]) if len(sys.argv)>2 else EXE,sys.argv[3] if len(sys.argv)>3 else TEST/'fixtures.json')
 elif mode=='native':
  import importlib.util
  spec=importlib.util.spec_from_file_location('native',TEST/'native.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  assert m.cases()==json.load(open(TEST/'fixtures.json'))['cases'];assert not m.AUDIT['unexpected_pcs'];(OUT/'native-pc-audit-replay.json').write_text(json.dumps(m.AUDIT,indent=2)+'\n');print('Fresh 595 ARM cases reproduce fixtures, fail-closed PC audit passed')
