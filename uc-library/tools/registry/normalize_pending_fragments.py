#!/usr/bin/env python3
"""Normalize explicit canonical/raw pending candidates for the unchanged merger.

Canonical membership pointers are not native behavior proofs. Never run this
against ACTIVE or write any database; output is a new reviewable raw fragment.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import registry as reg
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from merge_readiness import ValidationCache

def identity(row):return row['original_elf_sha256'],row['mangled']
def digest_value(value):return hashlib.sha256(reg.encode(value).encode()).hexdigest()

def normalize_entry(row,kind):
    if kind not in ('canonical','raw'):raise ValueError('Explicit canonical/raw source kind required')
    if row.get('portable_ready') is not False or row.get('cpp_compiled') is not True or row.get('mangling_namespace_checked') is not True:
        raise ValueError('Pending flags must remain explicit and passing')
    out=dict(row)
    if kind=='canonical':
        if row.get('behavior_validation'):
            if not isinstance(row.get('behavior_validation_sha256'),str):raise ValueError('Native behavior proof digest missing')
            out['validation']=row['behavior_validation'];out['validation_sha256']=row['behavior_validation_sha256']
        else:
            out.pop('validation',None);out.pop('validation_sha256',None)
    elif row.get('behavior_validation') and row.get('validation')!=row['behavior_validation']:
        raise ValueError('Distinct native and membership pointers in raw input; classify this input explicitly canonical')
    assert {k:v for k,v in out.items() if k not in ('validation','validation_sha256')}=={k:v for k,v in row.items() if k not in ('validation','validation_sha256')}
    return out

def merged_entry(raw,outer_path,outer_sha):
    out=dict(raw)
    if raw.get('validation'):
        out['behavior_validation']=raw['validation'];out['behavior_validation_sha256']=raw['validation_sha256']
    out.update(validation=outer_path,validation_sha256=outer_sha)
    return out

def normalize(library,canonical,raw,output):
    library=Path(library).resolve();output=Path(output).resolve()
    if not output.is_relative_to(library):raise ValueError('Output must be a new library-local candidate artifact')
    receipt=output.with_suffix(output.suffix+'.normalization.json')
    if output.exists() or receipt.exists():raise ValueError('Refusing to overwrite previous fragment/receipt')
    entries=[];seen=set();journal=[];inputs={};origins=[];cache=ValidationCache()
    for kind,paths in (('canonical',canonical),('raw',raw)):
        for source in paths:
            path=Path(source).absolute();before=cache.sha(path);payload=cache.read_json(path);rows=payload['functions'] if isinstance(payload,dict) else payload
            if not isinstance(rows,list):raise ValueError('Input must contain function records')
            for row in rows:
                key=identity(row)
                if key in seen:raise ValueError('Duplicate pending original key across candidate inputs: '+str(key))
                seen.add(key)
                if kind=='canonical' and row.get('validation'):
                    membership=(library/row['validation']).absolute()
                    if not cache.resolve(membership).is_relative_to(library) or cache.sha(membership)!=row.get('validation_sha256'):
                        raise ValueError('Canonical previous membership proof/hash mismatch')
                    previous=cache.read_json(membership)
                    members=previous.get('functions',[]) if isinstance(previous,dict) else previous
                    if not isinstance(members,list) or not any(isinstance(v,dict) and v.get('original_elf_sha256')==key[0] and v.get('mangled')==key[1] and v.get('sources')==row.get('sources') and v.get('repository_sources',{})==row.get('repository_sources',{}) for v in members):
                        raise ValueError('Canonical previous membership does not cover the exact source/original key')
                entry=normalize_entry(row,kind)
                if entry.get('validation'):
                    proof=(library/entry['validation']).absolute()
                    if not cache.resolve(proof).is_relative_to(library) or cache.sha(proof)!=entry['validation_sha256']:raise ValueError('Native proof file/hash binding mismatch')
                    if kind=='raw':
                        value=cache.read_json(proof)
                        if isinstance(value,dict) and 'membership' in str(value.get('kind','')).lower():raise ValueError('Membership document cannot be relabeled native behavior; use canonical input')
                entries.append(entry);origins.append((kind,row))
                journal.append({'original_elf_sha256':key[0],'mangled':key[1],'source_kind':kind,'input':str(path),'canonical_previous_validation':row.get('validation') if kind=='canonical' else None,'canonical_previous_validation_sha256':row.get('validation_sha256') if kind=='canonical' else None,'native_behavior_validation':row.get('behavior_validation') if kind=='canonical' else row.get('validation'),'native_behavior_validation_sha256':row.get('behavior_validation_sha256') if kind=='canonical' else row.get('validation_sha256'),'native_proof_absent_preserved':not bool(entry.get('validation')),'all_non_validation_fields_sha256':digest_value({k:v for k,v in row.items() if k not in ('validation','validation_sha256')})})
            inputs[str(path)]=before
    cache.unchanged()
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(reg.encode({'kind':'normalized-raw-pending-fragment','native_behavior_credit_added':False,'functions':entries})+'\n')
    relative=str(output.relative_to(library));sha=reg.digest(output);expected=[]
    for entry,(kind,original) in zip(entries,origins,strict=True):
        after=merged_entry(entry,relative,sha)
        if kind=='canonical':
            assert {k:v for k,v in after.items() if k not in ('validation','validation_sha256')}=={k:v for k,v in original.items() if k not in ('validation','validation_sha256')}
        expected.append({'original_elf_sha256':identity(entry)[0],'mangled':identity(entry)[1],'expected_canonical_sha256':digest_value(after)})
    report={'passed':True,'preparation_only':True,'database_written':False,'count':len(entries),'inputs':inputs,'output':relative,'output_sha256':sha,'journal':journal,'expected_canonical':expected,'no_native_cpp_domain_flags_or_declaration_fields_changed':True,'native_behavior_absence_preserved':True,'outer_membership_contains_exact_sources_and_original_keys':True,'normalizer_sha256':reg.digest(Path(__file__)),'fresh_unique_files_hashed':len(cache.files),'cache_scope':'Fresh operation-local file/JSON cache; every logical path resolution and stat fingerprint checked before output and receipt'}
    cache.unchanged()
    receipt.write_text(json.dumps(report,indent=2)+'\n');return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--library',type=Path,required=True);p.add_argument('--canonical',type=Path,action='append',default=[]);p.add_argument('--raw',type=Path,action='append',default=[]);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if not a.canonical and not a.raw:p.error('At least one explicitly typed input required')
    result=normalize(a.library,a.canonical,a.raw,a.output);print(json.dumps({'passed':True,'count':result['count'],'output':result['output'],'sha256':result['output_sha256']}))
