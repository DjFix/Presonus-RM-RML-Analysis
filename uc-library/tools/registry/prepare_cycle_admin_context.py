#!/usr/bin/env python3
"""Prepare reviewed historical build/format metadata; never admit or copy code."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import adapter
import registry as reg

ALLOWED={'CMakeLists.txt','cmake/ProductionSourceGroups.cmake','validation/formatting.json'}
HEADER='include/presonus/surface_panel/ControlHelpers.hpp'

def key(row):return row['original_elf_sha256'],row['mangled']
def encoded_hash(value):return hashlib.sha256(reg.encode(value).encode()).hexdigest()

def prepare(library,archives,output,db=None,expected_header_keys=127):
    library=Path(library).resolve();archives=Path(archives).resolve();output=Path(output).resolve()
    if output.exists():raise ValueError('Refusing to overwrite previous preparation')
    info=json.loads(archives.read_text());rules=info['files']
    if set(rules)!=ALLOWED:raise ValueError('Only the explicitly approved build/format context paths are allowed')
    for name,item in rules.items():
        path=(library/item['archive']).resolve()
        if not path.is_relative_to(library) or reg.digest(path)!=item['sha256']:raise ValueError('Historical archive hash/path mismatch: '+name)
        if Path(name).suffix in ('.cpp','.hpp','.h'):raise ValueError('Implementation source cannot be historical context')
    output.mkdir(parents=True)
    output_relative=str(output.relative_to(library));journal=[];ready=[];pending=[];header_keys=[]
    with adapter.snapshot(library,db) as source:
        provenance=source.provenance()
        for status in ('ready','pending'):
            for old in source.load_registry(status)['functions']:
                replay=HEADER in old.get('sources',{})
                if replay:header_keys.append({'original_elf_sha256':key(old)[0],'mangled':key(old)[1],'status':status})
                replacements={name:rules[name] for name in old.get('sources',{}) if name in rules}
                if not replacements:continue
                row=dict(old);sources={}
                for name,digest in old['sources'].items():
                    if name in replacements:
                        if digest!=rules[name]['sha256']:raise ValueError('Flat producer binding differs from exact archive: '+name)
                        sources[rules[name]['archive']]=digest
                    else:sources[name]=digest
                row['sources']=sources
                # Strictly prove every non-administrative binding and all metadata
                # (including native proof, domain, declaration and status) unchanged.
                original_native={n:h for n,h in old['sources'].items() if n not in ALLOWED}
                new_native={n:h for n,h in sources.items() if n not in {v['archive'] for v in rules.values()}}
                assert original_native==new_native
                assert {k:v for k,v in old.items() if k!='sources'}=={k:v for k,v in row.items() if k!='sources'}
                journal.append({'original_elf_sha256':key(old)[0],'mangled':key(old)[1],'status':status,'requires_real_header_replay':replay,'pure_metadata_admission_permitted':not replay,'old_validation':old.get('validation'),'old_validation_sha256':old.get('validation_sha256'),'native_source_bindings_sha256':encoded_hash(original_native),'repository_sources_sha256':encoded_hash(old.get('repository_sources',{})),'unchanged_non_source_metadata_sha256':encoded_hash({k:v for k,v in old.items() if k!='sources'}),'replacements':{name:{'role':'historical_build_or_format_producer_context','old_path':name,'archive_path':item['archive'],'sha256':item['sha256']} for name,item in replacements.items()}})
                (ready if status=='ready' else pending).append(row)
    if len(header_keys)!=expected_header_keys:raise ValueError('Unexpected real header-dependent workload: '+str(len(header_keys)))
    membership={'kind':'historical_build_format_context_membership_continuation','native_reexecuted':False,'hardware_verified':False,'scope':'Only exact archived build/format producer paths change. All real CPP/H/HPP/Core/source/behavior inputs remain active. Header-dependent keys require actual new family replays; this proof grants none.','functions':pending}
    membership_path=output/'pending-membership.json';membership_path.write_text(reg.encode(membership)+'\n');membership_sha=reg.digest(membership_path)
    pending_new=[dict(row,validation=output_relative+'/pending-membership.json',validation_sha256=membership_sha) for row in pending]
    replay_set={(v['original_elf_sha256'],v['mangled']) for v in header_keys}
    products={'ready-all-context.json':{'functions':ready},'pending-all-context.json':{'functions':pending_new},'ready-admin-only.json':{'functions':[v for v in ready if key(v) not in replay_set]},'pending-admin-only.json':{'functions':[v for v in pending_new if key(v) not in replay_set]},'classification-journal.json':{'records':journal},'header-replay-keys.json':{'requires_real_behavior_and_header_replays':header_keys}}
    for name,value in products.items():(output/name).write_text(reg.encode(value)+'\n')
    manifest={'preparation_only':True,'active_database_written':False,'archives':str(archives.relative_to(library)),'archives_sha256':reg.digest(archives),'source_classifier':{'allowed_historical_context':sorted(ALLOWED),'forbidden':'Any implementation CPP/H/HPP, Core implementation, active native/behavior source or real changed header','current_checks_retained':['current full formatting map and every current CPP/H/HPP digest','current CMake/build partition/compile-once and installed-role audits','new full Linux integration','actual new behavior/family replay for every header-dependent key']},'source_registry':provenance,'counts':{'ready_context':len(ready),'pending_context':len(pending_new),'ready_admin_only':sum(key(v) not in replay_set for v in ready),'pending_admin_only':sum(key(v) not in replay_set for v in pending_new),'header_replay_required':len(header_keys)},'native_cpp_domains_declarations_flags_statuses_changed':False,'ready_original_native_proof_changed':False,'pending_only_membership_validation_pointer_changed':True,'warning':'Never replace a freshly replayed header-family entry with these old native bindings. Root must merge archive-only producer changes with fresh family rows per original key, retaining all real new CPP/header/behavior inputs.','files':{str(p.relative_to(library)):reg.digest(p) for p in output.iterdir() if p.is_file()},'preparer_sha256':reg.digest(Path(__file__))}
    (output/'PREPARED.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--library',type=Path,required=True);p.add_argument('--archives',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--registry-db',type=Path);p.add_argument('--expected-header-keys',type=int,default=127);a=p.parse_args()
    result=prepare(a.library,a.archives,a.output,a.registry_db,a.expected_header_keys);print(json.dumps(result['counts']))
