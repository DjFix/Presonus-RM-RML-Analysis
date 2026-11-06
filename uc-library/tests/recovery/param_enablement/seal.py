"""Run local gates and write one hash-bound delivery per sealed task."""
import datetime,hashlib,json,subprocess,time
from pathlib import Path
import check,native
R=check.R;T=check.T
E=R/'evidence/recovery/2026-11-06/rolling200-03/enablement-implementation01';E.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256((R/p).read_bytes()).hexdigest()
def rel(p):return str(p.relative_to(R))
checks=[dict(kind=k,argv=['uc-library/.venv/bin/python',rel(T/'check.py'),k],timeout_seconds=180) for k in ['format','compile','symbols','native','replay']]
logs=[]
for c in checks:
 start=time.monotonic();p=subprocess.run(c['argv'],cwd=R,text=True,capture_output=True);log=E/(c['kind']+'.log');log.write_text(p.stdout+p.stderr);logs.append(dict(**c,returncode=p.returncode,seconds=time.monotonic()-start,log=rel(log)));p.check_returncode()
paths=[('source',check.CPP),('header',check.HPP),('test',check.DRIVER),('replay',rel(T/'check.py')),('oracle',rel(T/'native.py')),('fixture',rel(T/'fixtures.json')),('producer',rel(T/'seal.py'))]
for p in ['core/portable/coreparams.h','core/portable/coreparams.cpp','core/public/corevector.h']:
 paths.append(('provider','third_party/ccl-framework/'+p))
for p in ['libcorelib.a','libpresonus_core_allocator.a']:paths.append(('provider_archive',check.LIB+p))
artifacts=[dict(kind=k,path=p,sha256=sha(p)) for k,p in paths]
proof=dict(version=1,date=datetime.datetime.now(datetime.timezone.utc).isoformat(),elf_sha256=native.SHA,ranges=native.RANGES,checks=logs,artifacts=artifacts,formatter=check.run(['uc-library/.venv/bin/clang-format','--version']),compiler=check.run(['/usr/bin/c++','--version']),oracle='Unicorn original application instructions; provider hooks return explicitly supplied float bit patterns, equality, collection append and detach traces; no Core firmware executed',cases=1740,cpp_compared_cases=1620,host_destructors='D1 and D2 compiler variants checked separately by exact names; host compiler aliases their addresses, unlike distinct original ranges.',provider_tests='Real CCL duplicate observer notifications; range messages ignored; actual detach after lifetime; no borrowed parameter deletion.',remarks='Original ordinary return declarations, inheritance and layout remain unresolved; source model uses real ParamObserverBase and Vector. No readiness or ARM ABI claim. Constructor is independent support.',limitations='Non-null live borrowed parameters; no reentrant mutation, allocation failure or exception unwinding comparison. Native provider calls are bounded hooks, host provider separately real CCL; original Core behavior is not claimed.')
proofpath=E/'proof.json';proofpath.write_text(json.dumps(proof,indent=2)+'\n')
artifacts.append(dict(kind='proof',path=rel(proofpath),sha256=sha(rel(proofpath))))
for log in logs:artifacts.append(dict(kind='log',path=log['log'],sha256=sha(log['log'])))
for i,req in enumerate(native.REQUESTS):
 packet=native.P/req['task_id']/'context.json';r=native.RANGES[i]
 original=dict(elf_sha256=native.SHA,firmware='RM/RML mixer 13731',role='server',**{k:r[k] for k in ['mangled','address','size','section']})
 h=dict(version=1,task_id=req['task_id'],namespace='Presonus::Panel',packet_manifest=rel(packet),originals=[original],artifacts=artifacts+[dict(kind='packet',path=rel(packet),sha256=sha(rel(packet)))],checks=checks,validation_domain='1740 original instruction observations; 1620 ordered getValue/enable differential cases across messages -1..6, direct changed, 0..4 dependency entries, 0..3 duplicate targets, signed zero, finite/negative/subnormal/infinity/NaN; 120 append/detach/destructor native cases; real CCL duplicate notification and lifetime tests.',limitations=proof['limitations']+' '+proof['remarks'],build_integration=dict(partition='RM/server exclusive, pending Root ownership audit',production_sources=[check.CPP],public_headers=[check.HPP],test_sources=[check.DRIVER],link_dependencies=['corelib','presonus_core_allocator'],ctest_argv=['uc-library/.venv/bin/python',rel(T/'check.py'),'replay','CANONICAL_EXECUTABLE',rel(T/'fixtures.json')],fixture=rel(T/'fixtures.json')))
 out=R/'uc-library/candidates'/req['task_id'];out.mkdir(parents=True,exist_ok=True);(out/'HANDOFF.json').write_text(json.dumps(h,indent=2)+'\n')
print(rel(proofpath))
