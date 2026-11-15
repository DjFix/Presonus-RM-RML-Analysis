"""Only hash-bound, completed compiler observation leaves may avoid payload copying."""
import json,pathlib,re,shlex
from context_runtime import ContextError,sha,fingerprint
from reuse_observations import _capture,_owner
PATTERN=re.compile(r'temp/recovery-work/dependency-graph/refresh/[0-9]+/observations/([A-Za-z0-9_.:-]+)/(ast\.json|0000\.json)')

def require(value,message):
    if not value:raise ContextError(message)
def regular(root,value):
    p=pathlib.Path(value);p=p if p.is_absolute() else root/p
    require(p.is_relative_to(root) and '..' not in p.parts and p.resolve()==p and p.is_file() and p.stat().st_nlink==1,'Unsafe compiler observation provenance/leaf: '+str(p));return p
def pinned(root,reference,cache):
    p=regular(root,reference['path']);stamp=fingerprint(p);key=(p,reference['sha256'])
    if key not in cache:
        require(sha(p)==reference['sha256'],'Compiler provenance hash mismatch');cache[key]=(stamp,json.loads(p.read_text()));require(fingerprint(p)==stamp,'Compiler provenance changed while reading')
    require(cache[key][0]==stamp,'Compiler provenance changed during capture');return cache[key][1]
def validate_record(root,relative,digest,record,cache,current=False,payload_hash=True):
    match=PATTERN.fullmatch(relative);require(match is not None,'Not restricted compiler AST/GCC payload')
    state=pinned(root,record['state'],cache);state_value=state['files'].get(relative);require((state_value.get('sha256') if isinstance(state_value,dict) else state_value)==digest,'Observation absent/different in hash-bound registered state')
    report_reference=record['report'];require(state['reports'].get(report_reference['path'])==report_reference['sha256'],'Registered report binding differs');report=pinned(root,report_reference,cache);p=report['observation_provenance'];receipt_reference=record['receipt'];require(pathlib.Path(p['reuse_receipt'])==root/receipt_reference['path'] and p['sha256']==receipt_reference['sha256'],'Report reuse receipt binding differs');receipt=pinned(root,receipt_reference,cache)
    matches=[x for x in receipt['eligible'] if _owner(x['owner'])==match[1]];require(len(matches)==1,'Observation owner not uniquely eligible');entry=matches[0];require(entry['owner']==record['owner'],'Compiler owner differs')
    current_dir=root/pathlib.Path(relative).parent;origin=pathlib.Path(entry['source_directory']);require(PATTERN.fullmatch(str(origin.relative_to(root))+'/ast.json') is not None,'Original capture outside restricted numeric refresh observations')
    require(current_dir.parent.resolve()==current_dir.parent,'Compiler observation directory traverses unrecorded symlink')
    direct_directory_link=(current_dir.is_symlink() and str(current_dir.readlink())==str(origin) and current_dir.resolve()==origin)
    # Read-only snapshot overlays normalize an original directory link into a
    # copied directory whose AST/GCC leaves point to that exact physical origin.
    payload=current_dir/match[2]
    normalized_snapshot_leaf=(not current and not payload_hash and current_dir.resolve()==current_dir
        and payload.is_symlink() and str(payload.readlink())==str(origin/match[2]) and payload.resolve()==origin/match[2])
    require(direct_directory_link or normalized_snapshot_leaf,'Reference must match exact recorded original capture link/normalized snapshot leaf')
    require(pathlib.Path(entry['destination_link'])==current_dir,'Eligible destination differs');field='ast' if match[2]=='ast.json' else 'gcc';leaf=regular(root,entry[field+'_path']);require(leaf==origin/match[2] and entry[field+'_sha256']==digest,'Original physical leaf identity/hash differs')
    metadata={name:pinned(root,ref,cache) for name,ref in receipt['source_metadata'].items()};require(set(metadata)=={'plan.json','units.json','extract.json'},'Incomplete original capture provenance')
    for name,ref in receipt['source_metadata'].items():require(pathlib.Path(ref['path'])==origin.parents[1]/name,'Original capture metadata path differs')
    plan=metadata['plan.json'];require(plan['producer_sha256']==receipt['original_plan_producers'],'Original extraction producer identities differ');extracted=metadata['extract.json'];require(extracted==receipt['original_extract'] and type(extracted.get('returncode')) is int and extracted['returncode']==0,'Original extraction did not complete')
    tokens=[token for arg in extracted['argv'] for token in shlex.split(arg)];require(tokens[-2:]==[str(root/'dependency-graph/refresh_extract.py'),str(origin.parents[1])],'Original extraction command/output differs')
    rows=[row for owner,row in metadata['units.json'] if owner==entry['owner']];require(len(rows)==1,'Original compile owner/command missing or ambiguous')
    # Initial capture additionally replays maintained real-input/context/dump validation.
    # Historical snapshot reuse retains its original immutable input domain instead
    # of pretending that old captures executed against subsequently edited sources.
    if current:
        capture_key=('capture',origin,entry['owner'])
        if capture_key not in cache:cache[capture_key]=_capture(root,origin.parents[1],entry['owner'],rows[0],plan)[1]
        binding=cache[capture_key]
        for name in ('ast_sha256','gcc_sha256','input_sha256'):require(binding[name]==entry[name],'Real original compiler input/pair binding differs')
    if payload_hash:require(sha(leaf)==digest,'Compiler observation payload changed')
    if isinstance(state_value,dict) and 'fingerprint' in state_value:require(fingerprint(leaf)==state_value['fingerprint'],'Registered compiler observation fingerprint differs')
    return leaf

def candidate(root,relative,digest,files,cache):
    if not PATTERN.fullmatch(relative):return None
    # Only actual registered-state/reuse receipts are eligible, never arbitrary
    # compiler-shaped files or a mutable build/output path.
    active_path=root/'dependency-graph/ACTIVE.json';require(files.get('dependency-graph/ACTIVE.json')==sha(active_path),'Current graph pointer not frozen');active=json.loads(active_path.read_text());require(files.get(active['state'])==active['state_sha256'],'Current registered state not frozen');state_ref={'path':active['state'],'sha256':active['state_sha256']};state=pinned(root,state_ref,cache)
    report_path=str(pathlib.Path(relative).parents[2]/'refresh-report.json')
    if report_path not in state['reports']:return None
    report_ref={'path':report_path,'sha256':state['reports'][report_path]};report=pinned(root,report_ref,cache)
    if not report.get('observation_provenance',{}).get('reuse_receipt'):return None
    receipt_path=pathlib.Path(report['observation_provenance']['reuse_receipt']);receipt_ref={'path':str(receipt_path.relative_to(root)),'sha256':report['observation_provenance']['sha256']};receipt=pinned(root,receipt_ref,cache);match=PATTERN.fullmatch(relative);owners=[x['owner'] for x in receipt['eligible'] if _owner(x['owner'])==match[1]]
    if not owners:return None
    require(len(owners)==1,'Duplicate eligible compiler owner');record={'state':state_ref,'report':report_ref,'receipt':receipt_ref,'owner':owners[0],'scope':'Completed original compiler capture only; immutable evidence reference, no current graph/native/readiness credit'};leaf=validate_record(root,relative,digest,record,cache,current=True);return leaf,record

def recheck(root,references):
    cache={}
    for relative,reference in references.items():
        if reference.get('kind')!='compiler_observation':continue
        leaf=validate_record(root,relative,reference['sha256'],reference['provenance'],cache)
        require(str(leaf)==reference['target'] and fingerprint(leaf)==reference['fingerprint'],'Compiler leaf target/fingerprint changed')
