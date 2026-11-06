"""Seal worker-local completed checks; does not perform readiness admission."""
import datetime,hashlib,json,subprocess,sys
from pathlib import Path
import check,native,unicorn
R=check.R;T=check.T
E=R/'evidence/recovery/2026-11-06/rolling200-03/mapping159-o3';E.mkdir(parents=True,exist_ok=True)
P='temp/recovery-work/rolling200-03/mapping159/prepared159/packets/rolling200_03_mapping159_01'
checks=[];results=[]
for kind in ['format','compile','symbols','native','replay']:
 argv=['uc-library/.venv/bin/python','uc-library/tests/recovery/surface_mapping_predicate/check.py',kind]
 p=subprocess.run(argv,cwd=R,text=True,capture_output=True)
 (E/(kind+'.log')).write_text(p.stdout+p.stderr);assert p.returncode==0,(kind,p.stdout,p.stderr)
 checks.append(dict(kind=kind,argv=argv,timeout_seconds=120));results.append(dict(kind=kind,argv=argv,exit_code=p.returncode,log=str((E/(kind+'.log')).relative_to(R))))
def digest(path):return hashlib.sha256((R/path).read_bytes()).hexdigest()
files=[*check.OWNED,'uc-library/src/surface_panel/ControlHelpers.cpp',*[str(x.relative_to(R)) for x in T.glob('*.py')],str((T/'fixtures.json').relative_to(R)),P+'/context.json',P+'/request.json',P+'/ELF_CONTEXT.md','third_party/ccl-framework/core/portable/corecomponent.h','third_party/ccl-framework/core/portable/coreparams.h']
def role(path):
 if path==check.OWNED[2]:return 'test'
 if path.endswith('/fixtures.json'):return 'fixture'
 if path.endswith('/check.py'):return 'replay'
 return 'source' if path.endswith(('.cpp','.hpp')) else 'dependency'
artifacts=[dict(kind=role(path),path=path,sha256=digest(path)) for path in files]
fixtures=json.loads((T/'fixtures.json').read_text())
proof=dict(timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),elf_sha256=native.SHA,ranges=fixtures['ranges'],artifacts=artifacts,checks=results,compiler=subprocess.check_output(['/usr/bin/c++','--version'],text=True).splitlines()[0],formatter=subprocess.check_output([str(R/'uc-library/.venv/bin/clang-format'),'--version'],text=True).strip(),python=sys.version,unicorn=unicorn.__version__,cases=len(fixtures['cases']),original_executions=2*len(fixtures['cases']),portable_executions=2*len(fixtures['cases']),native_provider_traces='all mapping calls/order compared with linked libc wrappers; production O3, driver O0; no fno-builtin required',native_memory='stack writes only; no object writes',compile_argv=check.COMPILE,core='real pinned CCL headers; no Core implementation execution needed by predicates')
proofpath=str((E/'proof.json').relative_to(R));(R/proofpath).write_text(json.dumps(proof,indent=2)+'\n')
artifacts += [dict(kind='proof',path=proofpath,sha256=digest(proofpath))]+[dict(kind='log',path=x['log'],sha256=digest(x['log'])) for x in results]
original=dict(elf_sha256=native.SHA,firmware='CS18AI surface 13840',role='client',mangled=native.NAME,address=713836,size=484,section=12)
handoff=dict(version=1,task_id='rolling200_03_mapping159_01',namespace='Presonus',packet_manifest=P+'/context.json',originals=[original],artifacts=artifacts,checks=checks,validation_domain='81 valid byte-string/null cases: all nine families, prefix-only, suffix, embedded, truncation, uppercase, 4096-byte tails/heads, high-byte mismatches; independently executes both original ARM predicate bodies; compares mapping provider call names/order and mapping/transport returns; native writes constrained to stack.',limitations=['Portable source bool return spelling pending original declaration; original inheritance, storage, vtable and ARM ABI not recovered.','Original libc PLT functions are semantic stubs (unsigned-byte strcmp difference and strstr first occurrence); no Core binary execution, hardware, malformed pointers or unterminated strings.','Provider comparison checks names/order; source libc strcmp nonzero magnitude is implementation-defined and not asserted.','ELF assembler labels bind external libc providers with distinct C++ identifiers; validated GCC/Linux, no claim for other object formats or whole-program LTO.','Global build/full Linux role and installed audits/readiness admission remain Root-owned.'],build_integration=dict(production_partition='CS18 OBJECT (client-only original symbol)',sources=[check.OWNED[1]],public_headers=[check.OWNED[0]],test_targets=['surface_mapping_predicate_replay'],link_dependencies=['existing ControlHelpers.cpp production object; pinned CCL headers; libc'],test_sources=[check.OWNED[2]],link_options=['-Wl,--wrap=strstr','-Wl,--wrap=strcmp'],compile_options=[],optimization_validation={'production':'-O3','driver':'-O0','production_override_required':False},ctest_argv=['uc-library/.venv/bin/python','uc-library/tests/recovery/surface_mapping_predicate/check.py','replay','<canonical-built-executable>','uc-library/tests/recovery/surface_mapping_predicate/fixtures.json']))
H=R/'uc-library/candidates/rolling200_03_mapping159_01/HANDOFF.json';H.parent.mkdir(parents=True,exist_ok=True);H.write_text(json.dumps(handoff,indent=2)+'\n')
import importlib.util
spec=importlib.util.spec_from_file_location('accept_worker',R/'uc-library/tools/recovery/accept_worker.py');validator=importlib.util.module_from_spec(spec);spec.loader.exec_module(validator);validator.validate(handoff)
(E/'schema-validation.json').write_text(json.dumps(dict(stock_validate_passed=True,handoff_sha256=digest(str(H.relative_to(R)))),indent=2)+'\n')
print(H.relative_to(R),digest(str(H.relative_to(R))))
