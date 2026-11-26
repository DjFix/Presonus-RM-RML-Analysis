"""Linux local checks and hash-bound HANDOFF v1 for the exact five DAW packets."""
import argparse,datetime,json,os,pathlib,shlex,subprocess,time
import unicorn,elftools
from native import observe,context,PACKETS,sha
HERE=pathlib.Path('uc-library/tests/recovery/daw_mixer_five')
SOURCE='uc-library/src/Presonus/Surface/DAWMixerHandler.cpp'
HEADER='uc-library/include/presonus/surface/DAWMixerHandler.hpp'
TEST=str(HERE/'Replay.cpp')
WORK=pathlib.Path('temp/recovery-work/daw-mixer-five-build')
PYTHON='uc-library/.venv/bin/python'
FMT='uc-library/.venv/bin/clang-format'
CANON=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis')
CORE=CANON/'temp/core-upstream/root-integration-01'
ARCHIVES=[CORE/'libpresonus_cs18_components.a',CORE/'upstream-core/sdk/lib/libcorelib.a',CORE/'upstream-core/sdk/lib/libpresonus_core_allocator.a',CORE/'upstream-core/build/libpresonus_zlib.a']
PROVIDERS=['uc-library/src/Presonus/'+p+'.cpp' for p in ['DAWClientComponent','DAWChannel','DAWChannelGroup','MappingTable','MappingTableConnect','MappingTableAddItem','MappingTableItem','ColorMapping','Surface/PageParam']]
FLAGS=['c++','-std=c++17','-O2','-fno-rtti','-fno-lto','-ffunction-sections','-fdata-sections','-Iuc-library/include','-Ithird_party/ccl-framework','-Wno-multichar','-Ulinux']
WRAPS=['-Wl,--wrap=_ZN8Presonus12MappingTable7connectEPKcPN4Core8Portable9ParameterES2_b','-Wl,--wrap=_ZN8Presonus12MappingTable15setControlColorEPKcS2_']
TASKS=['sqlite24_daw_mixer_'+n for n in ['12e6de1da9','e5aad81421','b6a7630a2c','7d2117c1ce','c2aa2c2a23']]
def digest(p):return sha(pathlib.Path(p).read_bytes())
def write(p,d):p=pathlib.Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2)+'\n')
class Check:
 def __init__(self):WORK.mkdir(parents=True,exist_ok=True);self.log=[];self.units=[SOURCE,TEST,*PROVIDERS];self.objects=[WORK/f'unit{i}.o' for i in range(len(self.units))];self.exe=WORK/'replay'
 def run(self,*args):
  argv=list(map(str,args));start=time.monotonic();p=subprocess.run(argv,text=True,capture_output=True,env={**os.environ,'TMPDIR':str(WORK.resolve())});self.log.append(dict(argv=argv,returncode=p.returncode,seconds=time.monotonic()-start,stdout=p.stdout,stderr=p.stderr));
  if p.returncode:raise RuntimeError(shlex.join(argv)+'\n'+p.stdout+p.stderr)
  return p.stdout
 def format(self):self.run(FMT,'--style=file','--fallback-style=LLVM','--dry-run','--Werror',HEADER,SOURCE,TEST)
 def compile(self):
  for path in (WORK/'SUPPLEMENT.json',WORK/'DIRECT-PROVIDER-CLOSURE.json'):assert path.exists()
  closure=json.loads((WORK/'DIRECT-PROVIDER-CLOSURE.json').read_text())
  for row in closure['compiled_direct_dependencies']:assert digest(row['path'])==row['worker_sha256'],row
  for src,obj in zip(self.units,self.objects):self.run(*FLAGS,'-MMD','-c',src,'-o',obj)
  self.run('c++',*self.objects,*WRAPS,'-Wl,--gc-sections','-Wl,-Map='+str(WORK/'link.map'),'-Wl,--start-group',*ARCHIVES,'-Wl,--end-group','-lm','-pthread','-o',self.exe)
 def symbols(self,task):
  out=self.run('nm','--defined-only',self.objects[0]);names=[r['mangled'] for r in context(task)['task']['originals']]
  rows=[line for line in out.splitlines() if line.split()[-1] in names];assert len(rows)==len(names);assert all(line.split()[-2]=='T' for line in rows);return rows
 def replay(self,task,exe=None,fixture=None,refresh=False):
  fixture=pathlib.Path(fixture or HERE/'fixtures.json');native=observe(task)
  recorded={} if refresh and not fixture.exists() else json.loads(fixture.read_text())
  if refresh:recorded[task]=native;write(fixture,recorded)
  else:assert native==recorded[task], 'Native fixtures changed'
  for i,case in enumerate(native['cases']):
   result=self.run(exe or self.exe,native['method'],*[f'{k}={v}' for k,v in case['input'].items()]).splitlines()
   expected=['|'.join('-' if x is None else str(x) for x in row) for row in case['trace']]
   assert result==expected,(task,i,case['input'],next(((j,a,b) for j,(a,b) in enumerate(zip(result,expected)) if a!=b),None),len(result),len(expected))
  print(task,'matched',len(native['cases']),'ARM/Linux cases',flush=True)
  return native
 def dependencies(self):
  paths=set(self.units+[HEADER])
  for obj in self.objects:
   text=obj.with_suffix('.d').read_text().replace('\\\n',' ');paths.update(shlex.split(text.split(':',1)[1]))
  return sorted(paths)
 def seal(self,task,native,started):
  candidate=pathlib.Path('uc-library/candidates')/task;candidate.mkdir(parents=True,exist_ok=True)
  packet=PACKETS/task/'CONTEXT.json';details=context(task)['task'];originals=[dict(elf_sha256=o['elf'],**{k:o[k] for k in ['firmware','role','mangled','address','size','section']}) for o in details['originals']]
  domain='Exact CS18AI 13840 ARM range execution versus Linux source port with actual DAWClientComponent, DAWChannel, DAWChannelGroup, MappingTable, PageParam, CCL components/parameters and ColorMapping provider. '+str(len(native['cases']))+' cases: '+str(list(native['cases'][0]['input']))+'. Real positive and absent app inputs; ordered connects/colors, alias originals and header-page associations; automation output asserted for selected routing.'
  limitations=['Original unencoded returns, original class storage/inheritance and ARM ABI unresolved: declaration-pending portable reconstruction.', 'Borrowed DAWMixerState.client and group/table pointers explicitly assemble source-port storage; no native layout claim.', 'ARM CCL and app provider boundaries supply synthetic tag-parameter identities, typed casts, group used-count, named control/focus/type/color values and syncAutomation dispatch. Actual original getMixTargets and unlocked updatePan execute. Linux executes real typed providers and CCL independently; no hardware/device operations.', 'Bounded strip domain uses absent sends/cuemix folders, one valid channel type color (blue), missing/wrong channels, offsets 0/1/2, shift/meters and positive/negative filters; other state combinations remain unverified.', 'Native MappingTable::mapColor name-pointer result differs from existing legacy int source API. Explicit ColorMapping color-to-name provider adaptation matches existing MixerColorConverter pattern; no int-to-pointer cast.', 'Color call name/order is compared; real MappingTable executes with null panel controls, so actual panel LED transmission is excluded. Main group CCL cannot contain a child beyond its used count; malformed native storage excluded.']
  paths={p:'dependency' for p in self.dependencies()}
  paths.update({SOURCE:'source',HEADER:'source',TEST:'test',str(HERE/'native.py'):'oracle',str(HERE/'check.py'):'replay',str(HERE/'fixtures.json'):'fixture',str(packet):'packet',str(WORK/'SUPPLEMENT.json'):'dependency',str(WORK/'DIRECT-PROVIDER-CLOSURE.json'):'dependency'})
  versions=dict(compiler=self.run('c++','--version').splitlines()[0],formatter=self.run(FMT,'--version').strip(),unicorn=unicorn.__version__,pyelftools=elftools.__version__)
  symbols=self.symbols(task)
  proof=candidate/'worker-proof.json'
  write(proof,dict(version=1,task_id=task,originals=originals,native_range=native['original'],file_offset=native['file_offset'],native_case_count=len(native['cases']),portable_case_count=len(native['cases']),source_hashes={p:digest(p) for p in paths},archives={str(p):digest(p) for p in ARCHIVES},objects={str(p):digest(p) for p in self.objects},executable_sha256=digest(self.exe),symbols=symbols,versions=versions,checks=self.log,validation_domain=domain,limitations=limitations,proposed_classification='declaration-pending',canonical_binding_pending=True,session=dict(id=os.getenv('CODEX_THREAD_ID'),start=started,end=datetime.datetime.now(datetime.timezone.utc).isoformat())))
  paths[str(proof)]='proof'
  write(candidate/'HANDOFF.json',dict(version=1,task_id=task,namespace=details['namespace'],packet_manifest=str(packet),originals=originals,artifacts=[dict(kind=k,path=p,sha256=digest(p)) for p,k in paths.items()],checks=[dict(kind=mode,argv=[PYTHON,str(HERE/'check.py'),mode,task],timeout_seconds=240) for mode in ['format','compile','symbols','replay']],validation_domain=domain,limitations=limitations,build_integration=dict(production_partition='CS18',production_sources=[SOURCE],new_production_sources=[],public_headers=[HEADER],test_target='DawMixerFiveReplay',test_sources=[TEST],test_compile_options=['-fno-rtti'],test_link_options=WRAPS,link_dependencies=['presonus_cs18_components'],ctest_name=task,ctest_argv=[PYTHON,str(HERE/'check.py'),'replay',task,'--exe','$<TARGET_FILE:DawMixerFiveReplay>','--fixture',str(HERE/'fixtures.json')],ctest_working_directory='repository root')))
def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['format','compile','symbols','replay','all']);p.add_argument('task',nargs='?',choices=TASKS);p.add_argument('--exe');p.add_argument('--fixture');a=p.parse_args();c=Check();started=datetime.datetime.now(datetime.timezone.utc).isoformat()
 try:
  if a.mode=='all':
   c.format();c.compile();observed={t:c.replay(t,refresh=True) for t in TASKS}
   for task in TASKS:c.seal(task,observed[task],started)
  elif a.mode=='symbols':c.symbols(a.task)
  elif a.mode=='replay':c.replay(a.task,a.exe,a.fixture)
  else:getattr(c,a.mode)()
 finally:
  write(WORK/('check-log-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json'),c.log)
  write(WORK/'latest-check-log.json',c.log)
if __name__=='__main__':main()
