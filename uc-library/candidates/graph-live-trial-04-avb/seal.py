"""Local proof producer; does not admit readiness or edit shared files."""
import datetime,hashlib,json,os,subprocess,time
from pathlib import Path
import checks
B=checks.BASE
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def dump(p,d):Path(p).write_text(json.dumps(d,indent=2)+'\n')
commands=[('native',['uc-library/.venv/bin/python',str(B/'oracle.py')]),('format',checks.FORMAT),('compile',checks.COMPILE),('symbols',['uc-library/.venv/bin/python',str(B/'checks.py'),'symbols']),('replay',checks.REPLAY)]
results=[]
for label,argv in commands:
 start=utc();t=time.monotonic();r=subprocess.run(argv,text=True,capture_output=True);elapsed=time.monotonic()-t
 log=B/(label+'.log');log.write_text(r.stdout+r.stderr)
 results.append({'kind':label,'argv':argv,'started_utc':start,'ended_utc':utc(),'duration_seconds':elapsed,'returncode':r.returncode,'log':str(log),'log_sha256':sha(log)})
 assert r.returncode==0,(label,r.stderr,r.stdout)
fixture=json.loads((B/'fixtures.json').read_text());sources={str(Path(p).relative_to('uc-library')):sha(p) for p in checks.SOURCES}
repo_sources={}
mapfile=Path('uc-library/validation/core-upstream/source-map/server-functions.json');mapping=json.loads(mapfile.read_text());core=next(x for x in mapping['functions'] if x['mangled']=='_ZN4Core11DebugPrintfEPKcz')
for x in core['upstream']:
 p='third_party/ccl-framework/'+x['path'];assert sha(p)==x['source_sha256'];repo_sources[p]=sha(p)
pin=subprocess.check_output(['git','-C','third_party/ccl-framework','rev-parse','HEAD'],text=True).strip();assert pin=='e8cbdea4a4a20e15111f5a690798a259c0374b31'
proof={'version':1,'generated_utc':utc(),'worker_session_id':os.environ.get('CODEX_THREAD_ID'),'cpp_differential_passed':True,'compiled_mangled_names_matched':True,'portable_ready':False,'cpp_compiled':True,'mangling_namespace_checked':True,'original_declaration_verified':False,'original_arm_abi_verified':False,'hardware_verified':False,'sources':sources,'repository_sources':repo_sources,'fixture':str(B/'fixtures.json'),'fixture_sha256':sha(B/'fixtures.json'),'case_count':len(fixture['cases']),'native_execution_count':len(fixture['cases']),'commands':results,'ranges':fixture['ranges'],'elf':{'path':str(checks.Path('rootfs/RML16AI_Rack_13731/home/root/mixer')),'sha256':fixture['elf_sha256']},'formatter_version':subprocess.check_output(['uc-library/.venv/bin/clang-format','--version'],text=True).strip(),'compiler_version':subprocess.check_output(['/usr/bin/c++','--version'],text=True).splitlines()[0],'unicorn_version':__import__('unicorn').__version__,'producers':{str(B/p):sha(B/p) for p in ['oracle.py','replay.py','checks.py','seal.py']},'core':{'pin':pin,'mapping':str(mapfile),'mapping_sha256':sha(mapfile),'debug_provider':core,'library':checks.CORE,'library_sha256':sha(checks.CORE)},'validation_domain':'Observed native ordered calls, initialized routing packet fields and final four listener slots under 720 branch-covering cases, synthetic native object memory and required non-null manager results; original member instructions executed including nested targeted methods. Native pointer writes retained in fixtures; portable intermediate pointer writes are not independently instrumented.','limitations':fixture['exclusions']+['Original void return declarations, class layout, inheritance, enum representation and ARM ABI remain unresolved; void and fixed int enum are explicit source-port choices.','App-specific dependency services are required external boundaries; no production manager or routing provider recovered in this scope.','CS logging uses pinned official CCL DebugPrintf; its firmware body is not reconstructed.','Packet padding is intentionally excluded; independent RoutingPacket is not original packet/class layout.'],'functions':[]}
functions=[]
for i in range(1,6):
 packet=Path(f'temp/recovery-work/graph-live-trial-04/trial04_avb_{i}-packet');d=json.loads((packet/'context.json').read_text());o=d['originals'][0]['original'];record={'original_elf_sha256':o['elf'],'mangled':o['mangled'],'demangled':o['demangled'],'address':o['address'],'size':o['size'],'section':12,'firmware':o['firmware'],'role':o['role'],'cpp_compiled':True,'mangling_namespace_checked':True,'portable_ready':False,'sources':sources,'repository_sources':repo_sources,'validation_domain':proof['validation_domain'],'declaration_uncertainties':proof['limitations']};functions.append(record);proof['functions'].append(record.copy())
proof['mangled_names']=[x['mangled'] for x in functions];dump(B/'proof.json',proof)
for x in functions:x.update(validation='candidates/graph-live-trial-04-avb/proof.json',validation_sha256=sha(B/'proof.json'))
dump(B/'pending.fragment.json',{'functions':functions})
log=json.loads((B/'work-log.json').read_text());log['phase_timestamps'].append({'phase':'local_validation_sealed','utc':utc()});log['local_checks']=results;log['per_symbol_dependencies']=[{'mangled':x['mangled'],'actually_verified':['own native instructions and exact ELF section range','nested assigned method bodies','manager call signatures from one-hop relationships','initialized packet field stores' if i in (0,3,4) else 'listener index byte reads'],'protective':['Core source binding and real pinned DebugPrintf' if i in (0,1) else 'no Core body reconstruction'],'irrelevant':['broad Core DebugPrint call-closure fanout into unrelated application modules'],'unknown':['native original return/layout','manager and routing production providers','sender identity behind virtual call'],'context_requests':log['context_requests']} for i,x in enumerate(functions)];dump(B/'work-log.json',log)
print(json.dumps({'proof':str(B/'proof.json'),'native_cases':len(fixture['cases']),'checks':len(results)}))
