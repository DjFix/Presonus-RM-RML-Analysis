"""Root-authorized corrected Connection18 canonical provenance successor.
Unexecuted scratch delivery; original native/checker/fixtures remain unchanged.
"""
import argparse,datetime,hashlib,importlib.util,json,pathlib,shlex,subprocess,sys
from link_provenance import prove_link,sha as snapshot_sha,verify_snapshot
ROOT=pathlib.Path.cwd();HERE=pathlib.Path(__file__).resolve().parent

def digest(p):return snapshot_sha(p)
def bind(p):return {'path':str(p),'sha256':digest(p)}
def inside(p):
 p=p.resolve();assert p.is_relative_to(ROOT),p;return p
def main():
 for producer_input in [pathlib.Path(__file__).resolve(),HERE/'link_provenance.py',HERE/'ACCEPTED-GENERATION.json',HERE/'EIGHT-CONSUMERS.json',HERE/'EXTERNAL-CONSUMER-FIXTURES.json']:snapshot_sha(producer_input)
 ap=argparse.ArgumentParser();ap.add_argument('--exe',type=pathlib.Path,required=True);ap.add_argument('--build',type=pathlib.Path,default=pathlib.Path('temp/core-upstream/root-integration-01'));ap.add_argument('--out',type=pathlib.Path,required=True);ap.add_argument('--link-maps',type=pathlib.Path,required=True);a=ap.parse_args();exe=inside(a.exe);build=inside(a.build);out=inside(a.out);assert not out.exists();map_contract_path=inside(a.link_maps);map_contract=json.loads(map_contract_path.read_text());map_contract_before=bind(map_contract_path);contract=json.loads((HERE/'ACCEPTED-GENERATION.json').read_text());frozen=[]
 for x in contract['bindings']:
  p=inside(ROOT/x['path']);assert p.is_file() and digest(p)==x['sha256'],('Explicit source/runtime successor required',x['path']);frozen.append(bind(p))
 for path,h in json.loads((HERE/'EXTERNAL-CONSUMER-FIXTURES.json').read_text()).items():
  f=inside(pathlib.Path(path));assert digest(f)==h,path;frozen.append(bind(f))
 checker=ROOT/'uc-library/tests/recovery/connection_transport_eighteen/run_all.py';spec=importlib.util.spec_from_file_location('unchanged_connection18',checker);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.ROOT=ROOT;m.HERE=checker.parent;m.REPLAY_EXE=exe;m.PACKET_ROOT=ROOT/'temp/recovery-work/rolling-c001-20261124/packeting/sqlite-cycle02/connection_eighteen_sol61/eventitem-periodic-provenance01/support-sixpaths02';work=out.parent/(out.stem+'-commands');work.mkdir(exist_ok=False);m.WORK=work
 table=build/'compile_commands.json';table_before=bind(table);rows=json.loads(table.read_text());records=[];inputs={};observed=set();symbol_text={};commands=[]
 def run(argv):
  argv=list(map(str,argv));p=subprocess.run(argv,cwd=ROOT,text=True,capture_output=True);commands.append({'argv':argv,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr});assert p.returncode==0,commands[-1];return p.stdout
 def object_record(source):
  row,=[x for x in rows if pathlib.Path(x['file']).resolve()==ROOT/source];obj=inside(pathlib.Path(row['directory'])/row['output']);dep=pathlib.Path(str(obj)+'.d');assert obj.is_file() and dep.is_file(),(obj,dep)
  for name in shlex.split(dep.read_text().replace('\\\n',' ').split(':',1)[1]):
   p=pathlib.Path(name);p=(p if p.is_absolute() else pathlib.Path(row['directory'])/p).resolve();assert p.is_file();inputs[str(p)]=bind(p)
  item={'source':bind(ROOT/source),'object':bind(obj),'depfile':bind(dep),'actual_compile_entry':row};records.append(item);return item
 for name in m.PRODUCTION:
  source=m.SOURCE_PATHS[name];item=object_record(source);text=run(['nm','--defined-only',item['object']['path']]);symbol_text[source]=text;observed.update(line.split()[-1] for line in text.splitlines() if len(line.split())>=3)
 contexts=sorted((m.PACKET_ROOT/'tasks').glob('*/CONTEXT.json'));assert len(contexts)==27;originals=[x['original'] for p in contexts for x in json.loads(p.read_text())['originals']];assert len(originals)==54
 assert {x['mangled'] for x in originals}<=observed,({x['mangled'] for x in originals}-observed)
 driver=object_record('uc-library/tests/recovery/connection_transport_eighteen/Shared.cpp');parts=shlex.split(driver['actual_compile_entry']['command']);assert any(x in parts for x in ['-std=c++17','-std=gnu++17','-std=c++20','-std=gnu++20']);defs=[x for x in parts if x.startswith(('-DNDEBUG','-UNDEBUG'))];assert defs and defs[-1]=='-UNDEBUG';assert '-Ulinux' in parts and '-fno-lto' in parts and '-frtti' in parts
 def link_for(record):
  row=record['actual_compile_entry'];parts=pathlib.Path(row['output']).parts;p=pathlib.Path(row['directory'])/parts[0]/parts[1]/'link.txt';tokens=shlex.split(p.read_text());target=pathlib.Path(tokens[tokens.index('-o')+1]);target=target if target.is_absolute() else pathlib.Path(row['directory'])/target;return p,target.resolve(),tokens
 link,target,tokens=link_for(driver);assert target==exe and exe.is_file();wraps=['_ZdlPv','_ZdlPvm','getaddrinfo','connect','sendto','_ZN8Presonus2UC10Connection7processEb','select']
 for name in wraps:assert '-Wl,--wrap='+name in tokens,name
 # Source hash is already exact accepted corrected Shared.cpp; retain real delegation.
 shared=(ROOT/'uc-library/tests/recovery/connection_transport_eighteen/Shared.cpp').read_text();assert 'return __real__ZN8Presonus2UC10Connection7processEb(connection, drain);' in shared and 'return __real_select(n, read, write, error, timeout);' in shared
 _,libraries=m.settings();archives=[pathlib.Path(x) for x in libraries if isinstance(x,pathlib.Path) and x.suffix=='.a'];facade=build/'libpresonus_uc.a';archives=[facade,*archives];archive_before=[bind(p) for p in archives];members=run(['ar','t',facade]).splitlines()
 link_proofs=[prove_link(ROOT,build,exe,driver,rows,map_contract,run,{x['mangled'] for x in originals},archives)]
 links=[bind(link)];exe_before=bind(exe);start=datetime.datetime.now(datetime.timezone.utc).isoformat()
 # Original native verification and exact corrected frame/reset/nested Base projections.
 m.format_check()
 tasks=m.old_tasks();assert len(tasks)==18
 for task in tasks:
  if task=='sqlite_connection18_be5c94da558595e4':m.run([ROOT/'uc-library/.venv/bin/python',m.HERE.parent/task/'native.py','--verify'])
  else:m.native(task,verify=True)
 manifest=ROOT/'uc-library/candidates/connection_transport_eighteen/REMARKS.json'
 for path,h in json.loads(manifest.read_text())['fixtures'].items():assert digest(ROOT/path)==h,path
 m.run([exe]);m.compare_native_frames();m.compare_native_resets();m.compare_native_outgoing_process()
 consumers=[]
 for entry in json.loads((HERE/'EIGHT-CONSUMERS.json').read_text()):
  source=pathlib.Path(entry['source']).relative_to(ROOT);item=object_record(source);consumer_flags=shlex.split(item['actual_compile_entry']['command']);consumer_defs=[x for x in consumer_flags if x.startswith(('-DNDEBUG','-UNDEBUG'))];assert consumer_defs and consumer_defs[-1]=='-UNDEBUG',('Consumer assertions inactive',source)
  consumer_link,consumer_exe,_=link_for(item);assert consumer_exe.is_file();links.append(bind(consumer_link));before_exe=bind(consumer_exe);suffix=[str(ROOT/x) if x.startswith('uc-library/') else x for x in entry['argv_suffix']]
  if entry['source_port_replay']:
   argv=[ROOT/'uc-library/.venv/bin/python',ROOT/'uc-library/tools/source_port_replay.py','--executable',consumer_exe,'--fixtures',ROOT/'uc-library/validation/uc-outgoing-socket-identity/fixtures.stdin','--expected',ROOT/'uc-library/validation/uc-outgoing-socket-identity/expected.txt','--cases','180']
  else:argv=[consumer_exe,*suffix]
  undefined=set(line.split()[-1] for line in run(['nm','--undefined-only',item['object']['path']]).splitlines() if line.split());applicable=undefined&{x['mangled'] for x in originals}
  link_proofs.append(prove_link(ROOT,build,consumer_exe,item,rows,map_contract,run,applicable,archives))
  run(argv);assert bind(consumer_exe)==before_exe;consumers.append({'source':item['source'],'object':item['object'],'link':bind(consumer_link),'executable':before_exe,'actual_argv':list(map(str,argv))})
 assert len(consumers)==8
 hash_snapshot=verify_snapshot()
 for x in frozen+list(inputs.values())+links:assert digest(pathlib.Path(x['path']))==x['sha256']
 for item in records:
  for key in ['source','object','depfile']:assert digest(pathlib.Path(item[key]['path']))==item[key]['sha256']
 assert bind(map_contract_path)==map_contract_before
 for proof in link_proofs:
  for x in proof['bound_inputs']+[proof['map'],proof['link_file']]:assert digest(pathlib.Path(x['path']))==x['sha256']
 assert bind(table)==table_before and bind(exe)==exe_before and [bind(p) for p in archives]==archive_before
 proof={'version':1,'hash_snapshot':hash_snapshot,'attribution':'Root-authorized canonical corrected Connection18 source/native replay; original producers unchanged','start':start,'finish':datetime.datetime.now(datetime.timezone.utc).isoformat(),'executable':exe_before,'adapter':bind(pathlib.Path(__file__).resolve()),'original_checker':bind(checker),'accepted_contract':bind(HERE/'ACCEPTED-GENERATION.json'),'canonical_compile_table':table_before,'canonical_source_object_depfile_entries':records,'actual_inputs':list(inputs.values()),'actual_link_proofs':link_proofs,'link_map_contract':map_contract_before,'canonical_archives':archive_before,'facade_members':members,'original54identities':originals,'canonical_symbol_text':symbol_text,'driver_link':bind(link),'consumers':consumers,'adapter_commands':commands,'original_command_log':bind(work/'COMMANDS.jsonl'),'local_WORK_objects_or_symbolproof_used':False,'historical_compile_proof_relabelled':False,'actual_current_family_runs':1,'typed_references':27,'credit':'Only18methods27ABI54ELF; existing sender/helpers and corrected semantic fix0extra; SL6sub4pending handled separately, never blanket skipped.','limits':['Portable source/native call-boundary scope, not ARM ABI/hardware.','FullLinux/installed role/header closure/compileonce/format metadata/currentincumbent proofs/readiness remain separate mandatory gates.']}
 out.parent.mkdir(parents=True,exist_ok=True)
 with out.open('x') as f:json.dump(proof,f,indent=2);f.write('\n')
if __name__=='__main__':main()
