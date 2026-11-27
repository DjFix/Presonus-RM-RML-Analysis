# Scratch successor of immutable current84 sealer; see SEALER-SUCCESSOR-PROVENANCE01.json.
"""Versioned current104 provider-aware successor. Preparation by default; explicit owner release required."""
from concurrent.futures import ThreadPoolExecutor,as_completed
from functools import lru_cache
from pathlib import Path
from hashlib import sha256
import argparse,json,shlex,subprocess,sys,traceback
ROOT=Path.cwd();LIB=ROOT/'uc-library';BUILD='temp/core-upstream/root-integration-01'
HISTORY=ROOT/'temp/recovery-work/rolling-c001-20261124/integration-support/current104-proof-prep-sol61'
read=lambda p:json.loads(p.read_bytes())
sha=lambda p:sha256(p.read_bytes()).hexdigest()
sys.path.insert(0,str(LIB/'tools/recovery'))
from canonical_compile_bindings import bind,make_dependencies
from integration_preflight import verify_snapshot
from lpc_exact_elf_index import ExactElfIndex
ELF_INDEX=ExactElfIndex()
ROLE={'client':'cs18','server':'rm'}
ROLE_NAMES={'libpresonus_uc.a','libpresonus_cs18_components.a','libpresonus_rm_components.a'}
def exact_range(original):
    return ELF_INDEX.verify(ROOT,original)

def text_destructor_alias(path):
    from elftools.elf.elffile import ELFFile
    names=('_ZN8Presonus5Panel16TextEntryElementD1Ev','_ZN8Presonus5Panel16TextEntryElementD2Ev')
    with path.open('rb') as stream:
        elf=ELFFile(stream);symtab=elf.get_section_by_name('.symtab');entries=[]
        for name in names:
            row,=[x for x in symtab.get_symbol_by_name(name) or [] if x['st_shndx']!='SHN_UNDEF'];assert row['st_info']['type']=='STT_FUNC' and row['st_size']>0
            entries.append(dict(mangled=name,address=row['st_value'],size=row['st_size'],section=row['st_shndx']))
    assert entries[0]['address']==entries[1]['address'] and entries[0]['size']==entries[1]['size'] and entries[0]['section']==entries[1]['section'],'Text D1/D2 requires direct observation if compiled alias no longer holds'
    return dict(input=ref(path),symbols=entries,scope='Exact current compiled D1/D2 body alias. Native original ranges still checked independently; host automatic complete/base lifecycle observation applies only to this same-address/same-size body. No deleting destructor inference.')

def put(path,obj):
    with path.open('x') as stream:
        json.dump(obj,stream,indent=2)
        stream.write('\n')

def ref(path):
    return {'path':str(path.relative_to(ROOT)), 'sha256':sha(path)}

def run(argv, directory, log):
    with log.open('xb') as stream:
        subprocess.run(argv,cwd=directory,stdout=stream,stderr=subprocess.STDOUT,check=True)

@lru_cache(maxsize=None)
def symbols(path):
    return subprocess.check_output(['nm','-A','--defined-only',path],text=True).splitlines()

@lru_cache(maxsize=None)
def digest(path):
    return sha(path)

@lru_cache(maxsize=128)
def archive_members(path, basename, archive_sha):
    data=path.read_bytes()
    assert sha256(data).hexdigest()==archive_sha and data.startswith(b'!<arch>\n')
    pos=8
    longnames=b''
    result=[]
    while pos<len(data):
        header=data[pos:pos+60]
        assert len(header)==60 and header[58:]==b'`\n'
        size=int(header[48:58])
        member=data[pos+60:pos+60+size]
        assert len(member)==size
        name=header[:16].decode().strip()
        if name=='//':
            longnames=member
        elif name.startswith('#1/'):
            length=int(name[3:])
            name=member[:length].decode().rstrip('\0')
            member=member[length:]
        elif name.startswith('/') and name[1:].isdigit():
            name=longnames[int(name[1:]):].split(b'/\n',1)[0].decode()
        else:
            name=name.rstrip('/')
        if name==basename:
            result.append(sha256(member).hexdigest())
        pos+=60+size+size%2
    assert pos==len(data)
    return tuple(result)

def exact_archive_contains(path, wanted, basename):
    members=archive_members(path,basename,digest(path))
    assert members.count(wanted)<=1,(path,basename,wanted)
    return members.count(wanted)==1

def portable_command(command, exe, logdir):
    result=list(command)
    executables=[i for i,item in enumerate(result) if item.startswith(str(ROOT/BUILD)+'/')
                 and Path(item).is_file() and Path(item).suffix=='' and '/CMakeFiles/' not in item]
    assert executables and len({result[i] for i in executables})==1
    for pos in executables:result[pos]=str(exe)
    if '--out' in result and result[result.index('--out')+1]!='-':
        result[result.index('--out')+1]=str(logdir/'observations.json')
    return result

def normalized_compile_binding(binding):
    """Header observation traversal is unordered; retain exact entries/duplicates."""
    return {**binding, 'installed_core_bindings': sorted(
        binding['installed_core_bindings'], key=lambda item: json.dumps(item, sort_keys=True))}


def verify_context_transition(root, original, transitions):
    """Verify explicit historical context identity without relabeling its producer."""
    entry = transitions[original['path']]
    assert entry['role'] == 'historical_context_only'
    assert entry['original'] == original
    archived = root / entry['archived']['path']
    current = root / original['path']
    assert sha(archived) == entry['archived']['sha256'] == original['sha256']
    assert entry['current'] == {'path': original['path'], 'sha256': sha(current)}
    assert entry['reason'].strip()
    return entry


def seal(args):
    planpath=args.plan.resolve();plan=read(planpath);assert len(plan['registrations'])==133 and sum(len(r['originals']) for r in plan['registrations'])==248
    if not args.execute:
        print('Prepared only: 133 tasks/248 originals; owner full/installed/input release and reviewed matrices required.');return
    assert not plan['blocking_pre_execution'],'Actual manifest transition/gate blockers remain'
    for reg in plan['registrations']:
        reg['tests']=[{'name':reg['test'],'command':reg['ctest']}]
    assert sha(HISTORY/'updater_role104_r2.py')=='8ab0e00be2e621487711340c401966552c21601f82ae5a7a13a4583a32a72484','Role adapter provenance changed'
    assert sha(Path(__file__).with_name('lpc_exact_elf_index.py'))=='0d0eb118d4b79d56780cd30741415185a0c1959e1cbdc4150dc9d0c6ba1048e3','Exact original range cache changed'
    transition_path=args.integration_transition.resolve();transition=read(transition_path)
    assert transition['reviewer'].strip() and transition['approved'] is True
    context_transitions=transition['historical_context_inputs']
    context_paths={'AGENTS.md','uc-library/tests/recovery/rolling10_next100_surface_firmware_c1/check_current104_static.py'}
    assert set(context_transitions)==context_paths
    for name,item in plan['supplements'].items():
        if name=='current_instructions':
            assert item['path']=='AGENTS.md'
            verify_context_transition(ROOT,item,context_transitions)
        else:assert sha(ROOT/item['path'])==item['sha256'],'Bound mandatory supplement changed'
    for item in plan.get('versioned_driver_wrapper_inputs',[]):
        if item['path'] in context_paths:
            assert item['path']!='AGENTS.md'
            verify_context_transition(ROOT,item,context_transitions)
        else:assert sha(ROOT/item['path'])==item['sha256'],'Versioned driver/wrapper input changed'
    full=args.full.resolve();review=args.review.resolve();policy_path=args.provider_policy.resolve();out=args.out.resolve();native_path=args.native.resolve()
    decisions=read(review);policy=read(policy_path);native=read(native_path)
    for d in (decisions,policy):assert d['plan_sha256']==sha(planpath) and d.get('owner_review_required') is False,'Explicit owner-reviewed matrix required'
    semantic_review_path=ROOT/'temp/recovery-work/rolling-c001-20261124/integration-support/current104-provider-policy-review01/REVIEW.json'
    assert sha(semantic_review_path)=='c0fa0927bf8660602bd9879fcd74305de4787ef3db2e5c50d63589153acb9fc8'
    correction_path=HISTORY/'PROVIDER-STANDARD-RTTI-CORRECTION03.json'
    assert sha(correction_path)=='4c22209e8f4b2a041d5d5166afd2be476508c5bf84e67b9e31faccd884b3ccfc'
    correction=read(correction_path);standard_provider=Path(correction['actual_standard_provider']['path']);assert sha(standard_provider)==correction['actual_standard_provider']['sha256']
    assert correction['exact_weak_standard_symbol_exclusions']==['_ZTISt11logic_error','_ZTISt9exception']
    semantic_review=read(semantic_review_path);seeds=semantic_review['required_policy_promotions_lower_bound'];assert len(seeds)==64 and len({r['task'] for r in seeds})==34
    assert policy['semantic_correction_review']==ref(semantic_review_path)
    recorded={(r['task'],r['role']):set(r['providers']) for r in policy['mandatory_semantic_seeds']}
    assert len(recorded)==64
    registrations={r['task']:r for r in plan['registrations']}
    for seed in seeds:
        task=seed['task'];role=seed['role'];mandatory=set(seed['minimum_confirmed_runtime_promotions']);assert recorded[task,role]==mandatory
        requirement=policy['tasks'][task]['roles'][role];source='uc-library/'+registrations[task]['source']
        assert mandatory<=(set(requirement['required_runtime_providers'])|{source}),'Reviewed semantic runtime seed downgraded'
        assert not (mandatory-{source})&set(requirement['compiled_evidence_only']),'Runtime seed cannot be evidence-only'
    assert native['passed'] and native['plan']==ref(planpath)
    for unit in native['units'].values():
        assert unit['passed']
        for key in ('log','unit_result','generated'):
            if key in unit:assert sha(ROOT/unit[key]['path'])==unit[key]['sha256']
    linux=read(full/'COMPLETED.json')
    transition_path=args.integration_transition.resolve();transition=read(transition_path)
    assert transition['reviewer'].strip() and transition['approved'] is True
    assert transition['historical_plan']==ref(planpath) and transition['current_full']==ref(full/'COMPLETED.json')
    assert transition['current_source_snapshot']==ref(full/'source-snapshot.json')
    assert transition['previous_suite_count']==plan['expected_suite_count'] and transition['current_suite_count']==linux['test_suites']
    assert transition['unchanged_lpc_inputs_verified'] is True and transition['lpc_dependency_audit']['path'] and transition['lpc_dependency_audit']['sha256']
    assert sha(ROOT/transition['lpc_dependency_audit']['path'])==transition['lpc_dependency_audit']['sha256']
    assert linux['passed'] and linux['previous_suites_preserved']==transition['current_previous_suite_count']
    historical_inventory=read(ROOT/plan['inventory']['path']);current_inventory=read(full/'inventory.log')
    historical_tests={t['name']:t['command'] for t in historical_inventory['tests']}
    current_tests={t['name']:t['command'] for t in current_inventory['tests']}
    assert len(historical_tests)==plan['expected_suite_count'] and len(current_tests)==linux['test_suites']
    assert historical_tests.keys()<=current_tests.keys()
    selected_tests={r['test']:r['ctest'] for r in plan['registrations'] if r['group']=='lpc'}
    assert len(selected_tests)==16 and all(current_tests[name]==command for name,command in selected_tests.items())
    assert transition['historical_inventory']==ref(ROOT/plan['inventory']['path']) and transition['current_inventory']==ref(full/'inventory.log')
    historical_producers=transition['historical_producer_inputs']
    assert set(historical_producers)=={'uc-library/tools/recovery/sqlite_packet.py'}
    producer_binding=historical_producers['uc-library/tools/recovery/sqlite_packet.py']
    assert producer_binding['role']=='historical_packet_preparation_only'
    assert producer_binding['current']==ref(ROOT/'uc-library/tools/recovery/sqlite_packet.py')
    assert sha(ROOT/producer_binding['archived']['path'])==producer_binding['archived']['sha256']
    verify_snapshot(LIB,read(full/'source-snapshot.json'))
    install=next(x['argv'] for x in linux['commands'] if x['label']=='install');prefix=Path(install[install.index('--prefix')+1]);build=ROOT/BUILD
    integration=LIB/'validation/integration.json';formatting=LIB/'validation/formatting.json';assert sha(integration)==sha(LIB/'validation/integration-linux.json');assert read(integration)['test_suites']==linux['test_suites'];fmt=read(formatting)['files']
    assert sha(ROOT/plan['inventory']['path'])==plan['inventory']['sha256'];inventory={x['name']:x for x in read(full/'inventory.log')['tests']}
    compiler=read(build/'compile_commands.json');proofs=args.proof_dir.resolve();assert proofs.is_relative_to(LIB/'validation');proofs.mkdir(exist_ok=False);out.mkdir();role_root=args.role_proofs.resolve();role_completed=read(role_root/'COMPLETED.json');assert role_completed['passed'] and role_completed['tasks']==16
    import canonical_compile_bindings as bindings
    bindings.archive_contains=exact_archive_contains
    classifications={x['task']:{(r['original_elf_sha256'],r['mangled']):r['status'] for r in x['classifications']} for x in decisions['tasks']}
    def production_object(source):
        candidates=[x for x in compiler if Path(x['file'])==ROOT/source and 'CMakeFiles/presonus_' in x['output']];row,=candidates;return Path(row['directory'])/row['output']
    def verify(reg):
        task=reg['task'];location=out/task;location.mkdir();context=ROOT/reg['context']['path'];assert ref(context)==reg['context'];assert ref(ROOT/reg['handoff']['path'])==reg['handoff'];handoff=read(ROOT/reg['handoff']['path'])
        for a in reg['artifacts']:
            if a['path'] in historical_producers:
                assert a['sha256']==historical_producers[a['path']]['archived']['sha256']
            else:assert sha(ROOT/a['path'])==a['sha256'],a['path']
        for original in reg['exact_originals']:exact_range(original)
        for test in reg['tests']:assert inventory[test['name']]['command']==test['command'],test['name']
        source='uc-library/'+reg['source'];obj=build/reg['object'];assert sha(obj)
        for original in reg['exact_originals']:assert sum(line.split()[-1:]==[original['mangled']] for line in symbols(obj))==1
        nr=native['results'][task];assert nr['passed'] and nr['context']==reg['context'] and nr['handoff']==reg['handoff'];assert nr['inputs']=={a['path']:a['sha256'] for a in reg['artifacts']}
        roles={};rows=[];production={};core={};test_inputs={};alias_evidence={}
        text_dtor=reg['group']=='text' and any(o['mangled'] in ('_ZN8Presonus5Panel16TextEntryElementD1Ev','_ZN8Presonus5Panel16TextEntryElementD2Ev') for o in reg['exact_originals'])
        if text_dtor:alias_evidence['production_object']=text_destructor_alias(obj)
        for original in reg['exact_originals']:
            role=original['role'];role_tag=ROLE[role]
            if role not in roles:
                requirement=policy['tasks'][task]['roles'][role];required=set(requirement['required_runtime_providers']);evidence_only=set(requirement['compiled_evidence_only']);assert not required&evidence_only
                bag={a['path'] for a in reg['artifacts'] if a['path'].startswith('uc-library/src/') and a['path'].endswith('.cpp')}-{source};assert required|evidence_only==bag
                if reg['group']=='avb':
                    tests=[t for t in reg['tests'] if '--role' in t['command'] and t['command'][t['command'].index('--role')+1]==role];test,=tests
                else:test,=reg['tests']
                cmd=test['command'];exes=[Path(t) for t in cmd if t.startswith(str(build)+'/') and Path(t).suffix=='' and '/CMakeFiles/' not in t];exe,=set(exes)
                body_dso=build/'libUpdaterCanonicalBody.so' if reg['group']=='updater' else exe
                observed=bind(ROOT,obj,source,body_dso,required_provider_sources=tuple(sorted(required)),required_archive_names=('libcorelib.a','libpresonus_core_allocator.a','libpresonus_png.a','libpresonus_zlib.a'))
                compile_only={}
                for unit in sorted(evidence_only):compile_only[unit]=bind(ROOT,production_object(unit),unit)
                for obs in (observed,*compile_only.values()):
                    for path,digest_val in obs['files'].items():
                        if path.startswith(('uc-library/src/','uc-library/include/')):assert sha(ROOT/path)==digest_val==fmt[path.removeprefix('uc-library/')];production[path.removeprefix('uc-library/')]=digest_val
                        elif path.startswith('third_party/ccl-framework/core/'):core[path]=digest_val
                for path in handoff['build_integration'].get('ccl_dependency_paths',[]):core[path]=sha(ROOT/path)
                for item in handoff['artifacts']:
                    if item['path'].startswith('third_party/ccl-framework/core/'):assert sha(ROOT/item['path'])==item['sha256'];core[item['path']]=item['sha256']
                if reg['group']=='updater':
                    from updater_role104_r2 import bind_updater_role
                    folder=location/role;folder.mkdir()
                    role_record=bind_updater_role(ROOT,build,prefix,folder,reg,role,cmd,archive_members,digest,run,put,ref)
                    assert set(role_record['required_runtime_sources'])-{source}<=required,'Finite actual runtime providers missing reviewed task policy'
                    role_record.update(compile_and_link=observed,compiled_evidence_only=compile_only,provider_requirement=requirement)
                    roles[role]=role_record
                    linked={'link_file':role_record['replay_link_file']}
                else:
                    # Finite successor: reuse only hash-bound actual completed role executions.
                    from lpc_installed_role_reproof import strict_receipt
                    roleproof=role_root/task/'PROOF.json';assert ref(roleproof) in role_completed['proofs'];assert role_completed['producer']==ref(Path(__file__).with_name('lpc_installed_role_reproof.py'));rp=read(roleproof)
                    assert rp['passed'] and rp['task']==task and rp['handoff']==reg['handoff'] and rp['context']==reg['context']
                    assert rp['originals']==reg['exact_originals']
                    record=rp['roles'][role]
                    def check_refs(value):
                        if isinstance(value,dict):
                            if set(value)=={'path','sha256'}:assert sha(ROOT/value['path'])==value['sha256'],value['path']
                            for nested in value.values():check_refs(nested)
                        elif isinstance(value,list):
                            for nested in value:check_refs(nested)
                    check_refs(record)
                    assert normalized_compile_binding(record['compile_and_link'])==normalized_compile_binding(observed) and record['requirement']==requirement
                    linked=observed['link'];installed=ROOT/record['archive']['path'];mapping=ROOT/record['map']['path'];roleexe=ROOT/record['exe']['path'];folder=roleexe.parent
                    link=record['link_argv'];replay=record['replay_argv']
                    assert sum(a.startswith('-Wl,-Map,') for a in link)==1
                    assert '-Wl,-Map,'+str(mapping) in link
                    assert record['strict_runtime']==strict_receipt(replay)
                    static_receipt=record['strict_runtime']
                # Bind every actual replay translation unit and its real depfile, including shared test helpers.
                linkfile=ROOT/linked['link_file']['path'];target=linkfile.parent.name.removesuffix('.dir');test_units=[x for x in compiler if x['output'].startswith('CMakeFiles/'+target+'.dir/') and Path(x['file']).is_relative_to(LIB/'tests')];assert test_units
                unit_records=[]
                for testunit in test_units:
                    testobj=Path(testunit['directory'])/testunit['output'];dep=testobj.with_suffix(testobj.suffix+'.d');deps=make_dependencies(dep,Path(testunit['directory']),testobj);assert Path(testunit['file']) in deps;assert all(p.stat().st_mtime_ns<=testobj.stat().st_mtime_ns for p in deps)
                    unit_records.append({'object':ref(testobj),'depfile':ref(dep),'compile_entry':testunit});test_inputs.update({str(p.relative_to(ROOT)):sha(p) for p in deps if p.is_relative_to(ROOT)})
                if reg['group']=='updater':
                    roles[role]['test_objects']=unit_records
                else:roles[role]={'archive':ref(installed),'map':ref(mapping),'exe':ref(roleexe),'link_argv':link,'replay_argv':replay,'stdout':ref(folder/'replay.log'),'compile_and_link':observed,'compiled_evidence_only':compile_only,'provider_requirement':requirement,'test_objects':unit_records,'strict_local_runtime':static_receipt}
            if text_dtor:alias_evidence[role]=text_destructor_alias(ROOT/roles[role]['exe']['path'])
            assert sum(line.split()[-1:]==[original['mangled']] for line in symbols(ROOT/roles[role].get('symbol_table',roles[role]['exe'])['path']))==1
            status=classifications[task][(original['elf'],original['mangled'])];assert status in ('ready','pending');reason,=[t['reason'] for t in decisions['tasks'] if t['task']==task];limits=handoff['limitations'];limits=[limits] if isinstance(limits,str) else limits;assert limits and handoff['validation_domain']
            rows.append((status,{'original_elf_sha256':original['elf'],'mangled':original['mangled'],'original_address':original['address'],'original_size':original['size'],'original_section':original['section'],'role':role,'portable_ready':status=='ready','cpp_compiled':True,'mangling_namespace_checked':True,'sources':production,'repository_sources':core,'domain':handoff['validation_domain'],'declaration_uncertainties':[] if status=='ready' else [reason,*map(str,limits)]}))
        proof=proofs/(task+'.json');put(proof,{'passed':True,'cpp_differential_passed':True,'mangling_namespace_checked':True,'portable_ready':all(s=='ready' for s,r in rows),'functions':[r for s,r in rows],'exact_originals':reg['exact_originals'],'producer':ref(Path(__file__).resolve()),'historical_context_transitions':context_transitions,'historical_packet_producers':historical_producers,'proof_plan':ref(planpath),'current_integration_transition':ref(transition_path),'installed_role_successor':ref(role_root/task/'PROOF.json'),'integration':ref(integration),'formatting':ref(formatting),'native':{'canonical_native':ref(native_path),'result':nr},'checkout_context':reg['context'],'classification_review':ref(review),'provider_policy':ref(policy_path),'current_roles':roles,'test_inputs':test_inputs,'limitations':handoff['limitations'],'exact_variant_alias_evidence':alias_evidence,'provider_semantic_review':ref(semantic_review_path),'standard_runtime_ownership_correction':ref(correction_path),'mandatory_supplements':plan['supplements'],'versioned_driver_wrapper_inputs':plan.get('versioned_driver_wrapper_inputs',[]),'support_producers':[ref(Path(__file__).with_name(n)) for n in ('lpc_installed_role_reproof.py','lpc_exact_elf_index.py')]})
        for status,row in rows:row.update(validation=str(proof.relative_to(LIB)),validation_sha256=sha(proof))
        return rows
    selected=[r for r in plan['registrations'] if r['group']=='lpc'];assert len(selected)==16 and sum(len(r['originals']) for r in selected)==32
    expected_counts={status:sum(c['status']==status for r in selected for d in decisions['tasks'] if d['task']==r['task'] for c in d['classifications']) for status in ('ready','pending')}
    results={};errors={}
    with ThreadPoolExecutor(max_workers=4) as pool:
        work={pool.submit(verify,r):r['task'] for r in selected}
        for future in as_completed(work):
            task=work[future]
            try:results[task]=future.result()
            except Exception as exc:errors[task]={'exception':str(exc),'traceback':traceback.format_exc()}
    put(out/'TASK-RESULTS.json',{'passed_count':len(results),'failed_count':len(errors),'failures':errors});assert not errors,sorted(errors)
    members=[row for reg in selected for row in results[reg['task']]];assert len({(r['original_elf_sha256'],r['mangled']) for s,r in members})==32
    for status in ('ready','pending'):
        rows=[r for s,r in members if s==status];assert len(rows)==expected_counts[status];put(proofs/(status+'.fragment.json'),{'functions':rows})
    verify_snapshot(LIB,read(full/'source-snapshot.json'));put(out/'COMPLETED.json',{'passed':True,'tasks':16,'identities':32,'counts':expected_counts,'scope':'Finite LPC16 installed-role successor; includes separately labeled original helper identities; no registry admission','producer':ref(Path(__file__).resolve()),'integration':ref(integration),'formatting':ref(formatting),'provider_policy':ref(policy_path),'elf_cache':{'snapshots':ELF_INDEX.snapshots_built,'independent_range_checks':ELF_INDEX.range_checks},'fragments':[ref(proofs/(s+'.fragment.json')) for s in ('ready','pending')]})

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('plan',type=Path);parser.add_argument('full',type=Path);parser.add_argument('review',type=Path);parser.add_argument('native',type=Path);parser.add_argument('out',type=Path);parser.add_argument('--integration-transition',required=True,type=Path);parser.add_argument('--role-proofs',required=True,type=Path);parser.add_argument('--proof-dir',required=True,type=Path);parser.add_argument('--provider-policy',required=True,type=Path);parser.add_argument('--execute',action='store_true');seal(parser.parse_args())
