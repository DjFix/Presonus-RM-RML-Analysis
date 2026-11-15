import argparse,hashlib,json,os,subprocess,sys,datetime
from pathlib import Path
R=Path(__file__).resolve().parents[4];T=Path(__file__).resolve().parent;TASK=T.name;O=R/'temp/recovery-work'/TASK;O.mkdir(parents=True,exist_ok=True)
SOURCES=['uc-library/include/presonus/FocusRestorer.hpp','uc-library/src/Presonus/FocusRestorer.cpp'];OWNED=SOURCES+[str((T/'Replay.cpp').relative_to(R))]
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(argv,input=None):
 print(json.dumps(list(map(str,argv))),flush=True);p=subprocess.run(list(map(str,argv)),cwd=R,input=input,capture_output=True,text=True,env={**os.environ,'TMPDIR':str(O)});print(p.stdout,end='');print(p.stderr,end='',file=sys.stderr);p.check_returncode();return p.stdout

def compatibility(production):
 root=Path('/home/rs/projects/opencs/ai-line-analysis')
 receipt=root/'evidence/recovery/2026-11-14/rolling10x10/provider-supplements/historical-fixtures-01/RECEIPT.json'
 assert digest(receipt)=='d00ddffac3ee84e0a9c260a56186de017ac5588dc67b8e6b7bc5d413286fb24b'
 entries=json.loads(receipt.read_text())['records'];records=[]
 for name in ['rolling10_focus_01','rolling10_focus_03','rolling10_replacement_focus_01']:
  record=next(x for x in entries if x['task_id']==name);assert record['artifact_hashes_verified_against_handoff']
  files=record['files']
  get=lambda suffix: next(x for x in files if x['original_path'].endswith(suffix))
  replay=get('Replay.cpp');source=root/replay['immutable_capture'];assert digest(source)==replay['sha256']
  native=get('native.py');fixture=get('fixtures.json');npath=root/native['immutable_capture'];fpath=root/fixture['immutable_capture'];assert digest(npath)==native['sha256'] and digest(fpath)==fixture['sha256']
  run(['uc-library/.venv/bin/python',npath,'--verify'])
  exe=O/('compat-'+name)
  run(['c++','-std=c++17','-fno-rtti','-Wno-multichar','-ffunction-sections','-fdata-sections','-Iuc-library/include','-Ithird_party/ccl-framework',source,production,root/'temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a',root/'temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a',root/'temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a','-Wl,--gc-sections','-l:libpng16.so.16','-lz','-lpthread','-ldl','-lm','-o',exe])
  output=run([exe]);f=json.loads(fpath.read_text())
  if name=='rolling10_focus_01':
   assert all(x['state']=='00'*28 and x['first_char']==0 for x in f);assert list(map(int,output.split()))==[0]*8
  elif name=='rolling10_focus_03':
   lines=output.splitlines();assert len(lines)==len(f['cases'])
   for row,line in zip(f['cases'],lines):
    fields=line.split();assert list(map(int,fields[:7]))==row['state'];assert fields[7]==bytes.fromhex(row['name']).split(b'\0')[0].decode()
  else:assert list(map(int,output.split()))==[x['result'] for x in f['cases']]
  records.append(dict(task=name,frozen_replay=dict(path=str(source),sha256=digest(source)),native_producer=dict(path=str(npath),sha256=digest(npath),provenance='Immutable byte-exact historical producer captured by Root receipt with original HANDOFF artifact hash verified; fresh verification now uses this unchanged producer'),fixture=dict(path=str(fpath),sha256=digest(fpath),provenance='Immutable historical fixture capture bound to original HANDOFF artifact; original provenance preserved'),object_sha256=digest(production),executable_sha256=digest(exe),output=output,original_case_count=len(f) if isinstance(f,list) else len(f['cases'])))
 return dict(receipt=dict(path=str(receipt),sha256=digest(receipt)),replays=records)

def main():
 p=argparse.ArgumentParser();p.add_argument('mode',nargs='?',default='replay');p.add_argument('--exe');p.add_argument('--object');p.add_argument('--integration');p.add_argument('--out');p.add_argument('--provider-core');p.add_argument('--provider-allocator');a=p.parse_args();start_utc=datetime.datetime.now(datetime.timezone.utc).isoformat();import native
 if a.mode=='format':run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*OWNED]);return
 fixture=json.loads((T/'fixtures.json').read_text())
 if a.mode=='native':assert native.generate()==fixture;return
 if a.mode=='compile':
  flags=['c++','-std=c++17','-O0','-ffunction-sections','-fdata-sections','-fno-rtti','-Wno-multichar','-Iuc-library/include','-Ithird_party/ccl-framework']
  run([*flags,'-c',SOURCES[1],'-o',O/'production.o']);run([*flags,'-c',OWNED[2],'-o',O/'driver.o']);run(['c++',O/'production.o',O/'driver.o','-Wl,--gc-sections','/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a','/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a','-l:libpng16.so.16','-lz','-lpthread','-ldl','-lm','-o',O/'replay']);return
 obj=Path(a.object) if a.object else O/'production.o';exe=Path(a.exe) if a.exe else O/'replay'
 symbols=run(['nm','--defined-only',obj]);names={l.split()[-1] for l in symbols.splitlines() if l.split()};req=json.loads((native.PACKET/'request.json').read_text());assert req['targets'][0]['mangled'] in names
 if a.mode=='symbols':return
 assert native.generate()==fixture
 inventory=native.inventory(exe);assert inventory==fixture['provider_observations']
 ctor=native.generate(inventory,native.VARIANT if native.VARIANT.startswith('c') else 'c1')
 dtor=native.generate(inventory,native.VARIANT if native.VARIANT.startswith('d') else 'd1')
 payload=''
 for c,d in zip(ctor['cases'],dtor['cases']):
  ct=c['trace'];dt=d['trace'];payload+=' '.join(map(str,[sum(x[0]=='root' for x in ct),sum(x[0]=='focus' for x in ct),sum(x[0]=='client-rect' for x in ct),sum(x[0]=='root' for x in dt),sum(x[0]=='find-point' for x in dt),sum(x[0]=='set-focus' for x in dt)]+inventory[c['case']][-3:]))+'\n'
 output=run([exe],payload);assert len(output.splitlines())==11
 for row,line,dc in zip(inventory,output.splitlines(),dtor['cases']):
  calls=[x for x in dc['trace'] if x[0]=='set-focus'];assert list(map(int,line.split()))==[row[0],calls[0][1] if calls else row[5]]
 domain='11 actual CCL view-tree lifecycle scenarios per separate original variant: no root/no focus, retained focus, removed old view with matching replacement, name/geometry/focusability mismatch, new current root after reparenting, detached current root, overlapping rejected sibling, new root without match. Native target plus original FocusInfo ctor/setView execute; borrowed provider calls carry independently observed current-root/focus/geometry/Point-find results. Host lifetime cycle compares snapshot, final focus and independently observed actual onFocus event deltas; no D0/deallocation credit.'
 limitations=['Portable source port; original class layout/ARM ABI/hardware not established','Two C++ methods for four separately range-verified original variants; host C1/C2 and D1/D2 aliases recorded by nm, no claim native aliases','Actual stable CCL providers and NUL within captured32byte names; concurrent mutation/unknown overrides excluded','Original Core excluded; native Point-find result bridges actual provider and existing filter behavior; previous helper compatibility replay remains separate']
 sources={str(Path(x).relative_to('uc-library')):digest(R/x) for x in SOURCES}
 proof=dict(task_id=TASK,original_elf_sha256=native.SHA,mangled_names=[req['targets'][0]['mangled']],native=fixture,canonical_binding_pending=not bool(a.integration),compiled_mangled_names_matched=True,cpp_differential_passed=True,portable_ready=False,validation_domain=domain,limitations=limitations,sources=sources,repository_sources={},object=dict(path=str(obj),sha256=digest(obj)),executable=dict(path=str(exe),sha256=digest(exe)),formatter=run(['uc-library/.venv/bin/clang-format','--version']).strip())
 deps=['third_party/ccl-framework/core/portable/gui/coreview.h','third_party/ccl-framework/core/portable/gui/coreview.cpp','third_party/ccl-framework/core/portable/gui/coreviewshared.h','third_party/ccl-framework/core/public/corestringbuffer.h','third_party/ccl-framework/core/public/gui/corerect.h']
 proof['repository_sources']={x:digest(R/x) for x in deps}
 root=Path('/home/rs/projects/opencs/ai-line-analysis')
 paths=['temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a','temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a']
 proof['provider_archives']={x:digest(root/x) for x in paths}
 from elftools.elf.elffile import ELFFile
 with obj.open('rb') as f:
  elf=ELFFile(f);variants={z.name:z for z in elf.get_section_by_name('.symtab').iter_symbols()}
  proof['compiled_variant_symbols']={n:dict(section=elf.get_section(variants[n]['st_shndx']).name,offset=variants[n]['st_value'],size=variants[n]['st_size']) for n in ['_ZN8Presonus13FocusRestorerC1ERN4Core8Portable13ContainerViewE','_ZN8Presonus13FocusRestorerC2ERN4Core8Portable13ContainerViewE','_ZN8Presonus13FocusRestorerD1Ev','_ZN8Presonus13FocusRestorerD2Ev']}
 proof['session_id']='/root/rolling10_surface_input';proof['phase_timestamps']=dict(replay_start_utc=start_utc,replay_end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
 proof['provider_reference_output']=output
 proof['prior_helper_compatibility']=compatibility(obj)
 proof['original_elf_sha256']=native.SHA;proof['mangled_names']=[req['targets'][0]['mangled']]
 proof['original_constructor_destructor_declarations']='ABI constructor/destructor identities preserved; portable class layout unverified'
 if a.integration:proof['integration']=dict(path=a.integration,sha256=digest(R/a.integration))
 proof['proposed_readiness']=dict(ready=[],pending=[dict(original_elf_sha256=native.SHA,mangled=req['targets'][0]['mangled'],original_address=req['targets'][0]['address'],sources=sources,domain=domain,declaration_uncertainties=limitations,canonical_binding_pending=not bool(a.integration))])
 for entry in proof['proposed_readiness']['pending']:
  entry.update(portable_ready=False,cpp_compiled=True,mangling_namespace_checked=True,repository_sources=proof['repository_sources'])
 if a.out:Path(a.out).write_text(json.dumps(proof,indent=2)+'\n')
if __name__=='__main__':main()
