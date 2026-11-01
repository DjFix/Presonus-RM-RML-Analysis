#!/usr/bin/env python3
"""Seal worker-owned evidence, not readiness. Run after final checks."""
import datetime,hashlib,json,os,pathlib,shutil
ROOT=pathlib.Path(__file__).resolve().parents[3];BASE=pathlib.Path(__file__).parent
SCRATCH=ROOT/'temp/recovery-work/graph-live-trial-05/fx-worker'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def relative(p):return str(p.relative_to(ROOT))
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
fixtures=json.loads((BASE/'fixtures.json').read_text())
commands=[json.loads(s) for s in (SCRATCH/'commands.jsonl').read_text().splitlines()]
replay=json.loads((SCRATCH/'replay-run.json').read_text())
for name in ['commands.jsonl','replay-run.json','dependencies.d','symbol-check.log']:
 shutil.copyfile(SCRATCH/name,BASE/name)
sources=['uc-library/src/Presonus/Mixer/FXComponent.cpp','uc-library/include/presonus/mixer/FXComponent.hpp'];test='uc-library/tests/graph_trial05_fx_tests.cpp'
deps=sorted({part for part in (SCRATCH/'dependencies.d').read_text().replace('\\\n',' ').split() if part.startswith('third_party/')})
# Upstream sources can be added only by Root-expanded context, not guessed here.
extra=BASE/'expanded-dependencies.json'
if extra.exists():deps+=json.loads(extra.read_text())['files']
deps=sorted(set(deps))
per=[]
for i in range(1,6):
 packet=ROOT/f'temp/recovery-work/graph-live-trial-05/trial05_fx_{i}-packet'
 ctx=json.loads((packet/'native-context.json').read_text());root=ctx['roots'][0]
 edges=[]
 for e in ctx['edges']:
  target=e['dst'];node=ctx['nodes'].get(target,{})
  classification='used' if e['src']==root else 'irrelevant_to_bounded_target'
  reason='Target memory operand, branch or provider boundary reviewed; native oracle exercises it.' if classification=='used' else 'Incoming caller/table corroboration; no caller behavior reconstructed.'
  if e['src']==root and e['kind'] in ('ELF_CALLS','ELF_TAIL_BRANCH','ELF_UNRESOLVED'):
   classification='protected_boundary';reason='Original target executes; external implementation deliberately stubbed and trace-captured, not recovered.'
  edges.append({'edge_id':hashlib.sha256(json.dumps(e,sort_keys=True).encode()).hexdigest(),'edge':e,'classification':classification,'reason':reason})
 per.append({'task_id':f'trial05_fx_{i}','mangled':fixtures['ranges'][i-1]['mangled'],'reviewed_edge_bindings':edges,'unknown_dependencies':['Original return declaration, layout/inheritance/ownership, original virtual declarations; app boundary implementations excluded.'],'protected_dependencies':['Pinned actual CCL providers replace Core firmware; external app helpers traced as stubs.'],'irrelevant_dependencies':['Incoming caller bodies and graph-linked unrelated surface/update call closures not needed for bounded target implementation.'],'case_count':sum(c['args'][0]==i for c in fixtures['cases'])})
work={'provider_session_id':os.environ.get('CODEX_THREAD_ID'),'sealed_utc':now,'phase_times':{'source_creation_utc':'2026-11-01T10:19:23.785547130Z','test_creation_utc':'2026-11-01T10:19:28.740855102Z','native_original_execution':{k:fixtures[k] for k in ['started_utc','ended_utc','duration_seconds']},'portable_replay':{k:replay[k] for k in ['started_utc','ended_utc','duration_seconds']}},'commands':commands,'symbols':per,'context_requests':'See context-requests.json (Root owns baseline expansion); early tool/request timestamps require provider session timeline, not fabricated estimates.','failures':['Initial compile: inherited Parameter::info shadowed fixture info; corrected qualification.','Link: generic -lpng unavailable; used actual canonical .so.16 path.','Link: upstream RTTI absent; compile probes with -fno-rtti.','Initial compile failure was followed by one failed replay before executable existed; no evidence from failed replay used.'],'redundant_checks':['Final native replay repeated after producer gained manifest verification/timing fields.','Compile and replay retries retained in scratch/provider session timeline.'],'timing_limitations':['Initial packet reading and context-request dispatch were not independently clock-instrumented; exact events remain in provider session. No token estimates.'],'readiness_admitted':False}
write(BASE/'work-log.json',work)
proof={'version':1,'scope':'bounded portable source port, original declarations pending','checkout':str(ROOT),'elf_sha256':fixtures['elf_sha256'],'ranges':fixtures['ranges'],'native_execution':{'fixture':relative(BASE/'fixtures.json'),'fixture_sha256':sha(BASE/'fixtures.json'),'producer':relative(BASE/'native.py'),'producer_sha256':sha(BASE/'native.py'),'versions':fixtures['versions'],'case_count':len(fixtures['cases']),'boundary_stubs':['SLReverbController::setDirty','FXComponent::getTypeNum','FXComponent::updateFxTypeName','FXComponent::handleFXTypeChange','parameter virtual getValue/setValue','Core Component countParameters/getParameterAt','unsigned-to-float runtime conversion']},'portable_execution':replay,'formatting':{'version':'clang-format version 23.1.3','sources':{p:sha(ROOT/p) for p in [*sources,test]},'read_only_check_passed':True},'provider_dependencies':{p:sha(ROOT/p) for p in deps},'commands':commands,'per_symbol':per,'hardware_validated':False,'arm_abi_verified':False,'original_declaration_verified':False,'original_layout_verified':False,'behavior_scope':'Exact fixture observations for targets with explicit external boundary models; no full-application or Core native behavior claim.'}
write(BASE/'proof.json',proof)
integration={'production_partition':'RM','production_cpp':sources[0],'public_headers':[sources[1]],'test_target':'graph_trial05_fx_tests','test_cpp':test,'compile_options':['-fno-rtti'],'link_dependencies':['actual pinned CCL corelib and allocator','canonical private glibc29 provider and existing system dependencies'],'ctest_argv':['uc-library/.venv/bin/python',relative(BASE/'check.py'),'replay','--executable','$<TARGET_FILE:graph_trial05_fx_tests>','--fixtures',relative(BASE/'fixtures.json')],'fixture_sha256':sha(BASE/'fixtures.json')}
write(BASE/'build-integration.json',integration)
artifacts=[]
def artifact(kind,p):
 p=ROOT/p if isinstance(p,str) else p
 if relative(p) not in {a['path'] for a in artifacts}:artifacts.append({'kind':kind,'path':relative(p),'sha256':sha(p)})
for p in sources:artifact('source',p)
artifact('test',test)
for kind,name in [('fixture','fixtures.json'),('replay','check.py'),('producer','native.py'),('producer','seal.py'),('proof','proof.json'),('log','work-log.json'),('log','commands.jsonl'),('log','replay-run.json'),('log','dependencies.d'),('log','symbol-check.log'),('documentation','README.md'),('build_integration','build-integration.json')]:artifact(kind,BASE/name)
for p in deps:artifact('dependency',p)
for i in range(1,6):
 packet=ROOT/f'temp/recovery-work/graph-live-trial-05/trial05_fx_{i}-packet'
 for n in ['context.json','request.json','native-context.json','ELF_CONTEXT.md','TASK.md','SUBAGENT_PROMPT.md','SOURCE_SLICES.md','CONTEXT.md']:artifact('packet',packet/n)
for name in ['context-requests.json','expanded-dependencies.json']:
 if (BASE/name).exists():artifact('context',BASE/name)
supplement=ROOT/'evidence/recovery/2026-11-01/dependency-graph/live-trial-05-10x5'
for n in ['provider-context.json','parameter-vtable-data.json']:artifact('context',supplement/n)
for j in range(7,12):
 directory=ROOT/f'temp/recovery-work/graph-live-trial-05/expansions/{j:02d}-fx'
 for n in ['expansion-request.json','expansion.json','ELF_CONTEXT.md','native-context.json']:
  if (directory/n).exists():artifact('context',directory/n)
checks=[{'kind':kind,'argv':['uc-library/.venv/bin/python',relative(BASE/'check.py'),kind], 'timeout_seconds':120} for kind in ['format','compile','symbols','replay']]
index=[]
for i in range(1,6):
 original=fixtures['ranges'][i-1]
 handoff={'version':1,'task_id':f'trial05_fx_{i}','namespace':'Presonus::Mixer::FXComponent','packet_manifest':f'temp/recovery-work/graph-live-trial-05/trial05_fx_{i}-packet/context.json','originals':[{k:original[k] for k in ['elf_sha256','firmware','role','mangled','address','size','section']}],'artifacts':artifacts,'checks':checks,'validation_domain':per[i-1],'limitations':(BASE/'README.md').read_text(),'build_integration':integration}
 out=BASE/f'HANDOFF-{i}.json';write(out,handoff);index.append({'task_id':handoff['task_id'],'path':relative(out),'sha256':sha(out)})
write(BASE/'HANDOFF-INDEX.json',{'version':1,'provider_session_id':os.environ.get('CODEX_THREAD_ID'),'handoffs':index,'proof':relative(BASE/'proof.json'),'build_integration':relative(BASE/'build-integration.json')})
print(json.dumps(index,indent=2))
