"""Derived ELF equivalence and unique-work index. Never writes readiness."""
import argparse
import bisect
import re
import sys
import collections
import datetime
import hashlib
import io
import json
import pathlib
import sqlite3
import uuid

from context_runtime import ContextError, inside, sha
from native_context import open_index, target_key

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY = 'elf-dedup-v1'


def dump(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def digest(*values):
    return hashlib.sha256(dump(values).encode()).hexdigest()


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def connect(path, readonly=False):
    c = sqlite3.connect(pathlib.Path(path).resolve().as_uri() + ('?mode=ro' if readonly else '?mode=rw'), uri=True, timeout=60)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    return c


def meta(c, name):
    row = c.execute('SELECT value FROM index_meta WHERE key=?', (name,)).fetchone()
    if not row:
        raise ContextError('Incomplete dedup index: ' + name)
    return json.loads(row[0])


def decision(c, subject, kind, status, scope, reason, members, evidence=()):
    old = c.execute('SELECT * FROM equivalence_decisions WHERE subject_id=? ORDER BY revision DESC LIMIT 1', (subject,)).fetchone()
    fields = (kind, status, scope, reason, dump(sorted(members)), dump(evidence))
    if old and fields == tuple(old[k] for k in ('equivalence_kind','status','verification_scope','reason','members','evidence_refs')):
        return old['id']
    revision = old['revision'] + 1 if old else 1
    ident = digest(subject, revision, fields, meta(c, 'generation'))
    c.execute('INSERT INTO equivalence_decisions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
              (ident, subject, revision, *fields, __file__, sha(pathlib.Path(__file__)), POLICY, meta(c, 'generation'), now()))
    return ident


def add_work(c, kind, subject, members=(), representative=None, decision_id=None):
    ident = digest('work', kind, subject)
    c.execute('INSERT OR IGNORE INTO reconstruction_work_items(id,work_kind,subject_id,decision_id,representative) VALUES(?,?,?,?,?)',
              (ident, kind, subject, decision_id, representative))
    c.executemany('INSERT OR IGNORE INTO work_item_members VALUES(?,?)', [(ident, x) for x in members])
    return ident


def evaluate(c, members):
    """Conservative, nonrecursive proof rule. Unknown dependencies always block."""
    observations = [json.loads(c.execute('SELECT observations FROM dependency_observations WHERE occurrence_id=?', (x,)).fetchone()[0]) for x in members]
    blockers = sorted({b for x in members for b in json.loads(c.execute('SELECT blockers FROM dependency_observations WHERE occurrence_id=?', (x,)).fetchone()[0])})
    if blockers:
        return 'blocked', '; '.join(blockers)
    # Concrete payload content identities, instruction-relative sites and literal
    # values must agree. Names of callees alone never satisfy this rule.
    if len({dump(o) for o in observations}) != 1:
        return 'rejected', 'Observed dependency/data differences; exact bytes are insufficient'
    return 'verified', 'Complete exact code ranges, matching encoded interface and resolved dependency-free or exact-payload observations'


def build(native, pointer, out, root=ROOT, releases=()):
    """New generation only: preserve existing indexes. Exact reimport is no-op."""
    from elftools.elf.elffile import ELFFile
    sys.path.insert(0,str(root/'uc-library/tools/registry'))
    import adapter
    with adapter.snapshot(root/'uc-library') as snapshot:
        canonical_cpp_keys=sorted((r['elf'],r['mangled']) for r in snapshot.c.execute('SELECT elf,mangled FROM records'))
    producer_inputs={name:sha(pathlib.Path(__file__).with_name(name)) for name in ('dedup_index.py','dedup_work.py','dedup_schema.sql')}
    release_inputs={str(p.relative_to(root)):sha(p) for p in releases}
    generation = digest(pointer['sha256'], POLICY, producer_inputs,canonical_cpp_keys,release_inputs)
    db = out / 'dedup.sqlite'
    if db.exists():
        with connect(db, True) as c:
            if not meta(c,'complete'):raise ContextError('Incomplete preserved import; use a new output directory')
            if meta(c, 'generation') != generation:
                raise ContextError('Existing generation differs; use a new output directory')
            return report(c)
    out.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(db)
    c.row_factory = sqlite3.Row
    c.executescript(pathlib.Path(__file__).with_name('dedup_schema.sql').read_text())
    for k,v in {'schema_version':1, 'generation':generation, 'native_generation':pointer['sha256'], 'native_pointer':pointer, 'producer_sha256':sha(pathlib.Path(__file__)), 'policy':POLICY, 'producer_inputs':producer_inputs,'release_inputs':release_inputs}.items():
        c.execute('INSERT INTO index_meta VALUES(?,?)',(k,dump(v)))
    for provider in native.execute('SELECT * FROM providers'):
        c.execute('INSERT INTO external_providers VALUES(?,?)',(provider['id'],dump(dict(provider))))
    bodies = {r['id']:json.loads(r['payload']) for r in native.execute('SELECT * FROM bodies')}
    resolutions = {r['symbol_id']:dict(r) for r in native.execute('SELECT * FROM symbol_resolution')}
    all_nodes = {r['id']:dict(r) for r in native.execute('SELECT * FROM nodes WHERE kind IN ("NativeFunction","NativeData","NativeAddress")')}
    binaries = {}
    for binary in native.execute('SELECT * FROM binaries'):
        raw = inside(root,binary['path']).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=binary['id']:
            raise ContextError('ELF hash changed')
        elf = ELFFile(io.BytesIO(raw)); sections=list(elf.iter_sections())
        abi = dump([elf['e_machine'],elf.elfclass,elf.little_endian,elf['e_ident']['EI_OSABI'],elf['e_flags']])
        c.execute('INSERT INTO binary_artifacts VALUES(?,?,?,?,?,?)',(binary['id'],elf['e_machine'],elf.elfclass,'little' if elf.little_endian else 'big',abi,elf['e_flags']))
        c.execute('INSERT INTO binary_releases VALUES(?,?,?,?,?,?)',(digest(binary['id'],binary['firmware'],binary['role'],binary['path']),binary['id'],binary['firmware'],binary['role'],binary['path'],binary['metadata']))
        mappings=sorted((s['st_value'],s.name[1]) for s in elf.get_section_by_name('.symtab').iter_symbols() if s.name.split('.')[0] in ('$a','$t','$d'))
        relocations=[]
        for sec in sections:
            if hasattr(sec,'iter_relocations'):
                relocations.extend(dict(r.entry) for r in sec.iter_relocations())
        binaries[binary['id']] = (raw,elf,sections,mappings,abi,relocations)
    sys.path.insert(0,str(root/'uc-library/tools/registry'))
    import adapter
    with adapter.snapshot(root/'uc-library') as snapshot:
        catalog=[dict(r) for r in snapshot.c.execute('SELECT * FROM catalog_symbols') if r['elf'] in binaries]
        existing_cpp={(r['elf'],r['mangled']) for r in snapshot.c.execute('SELECT elf,mangled FROM records')}
    for manifest in releases:
        release=json.loads(manifest.read_text())
        elfsha=release['elf_sha256']
        if elfsha not in binaries or sha(inside(root,release['original_path']))!=elfsha:raise ContextError('Additional release must point to the same registered ELF bytes')
        values=(digest('release',release),elfsha,release['firmware_version'],release['role'],release['original_path'],dump({'manifest':str(manifest.relative_to(root)),'sha256':sha(manifest),'release':release}))
        c.execute('INSERT OR IGNORE INTO binary_releases VALUES(?,?,?,?,?,?)',values)
    native_to_occ={}
    for original in catalog:
        ident=target_key(original)
        if ident not in all_nodes:raise ContextError('Catalog anchor missing from native graph')
        node=all_nodes[ident]
        m=dict(original); b=bodies.get(ident); elfsha=node['elf']
        raw,elf,sections,mappings,abi,relocs=binaries[elfsha]
        anchor=str(m['anchor']); occurrence=digest('occurrence',elfsha,anchor)
        # Catalog anchors remain independent of the native node's range key.
        native_to_occ.setdefault(ident,[]).append(occurrence)
        section=json.loads(m['section_json']); range_id=None; mode=None
        if b:
            section_obj=sections[section]
            address=m['address'] & ~1 if m['kind']=='STT_FUNC' else m['address']
            if m['kind']=='STT_FUNC':
                values=[v for a,v in mappings if a<=address]
                mode=('thumb' if values and values[-1]=='t' or m['address']&1 else 'arm')
            if mode is not None:
                transitions=[(a-address,v) for a,v in mappings if address<a<address+m['size']]
                if transitions:mode=dump([mode,transitions])
            range_id=digest('range',elfsha,section,address,m['size'])
            content=b['bytes_sha256']; offset=b['file_offset']
            if offset is not None:
                if offset<0 or offset+m['size']>len(raw) or hashlib.sha256(raw[offset:offset+m['size']]).hexdigest()!=content:
                    raise ContextError('Full range hash mismatch')
            c.execute('INSERT OR IGNORE INTO binary_ranges VALUES(?,?,?,?,?,?,?,?,?,?,?)',(range_id,elfsha,section,section_obj.name,address,m['size'],offset,b['storage'],content,mode,'ELF symbol size and actual section mapping'))
            if node['kind']=='NativeData' and content:
                content_id=digest(m['size'],content)
                obj=out/'objects'/content
                obj.parent.mkdir(exist_ok=True)
                if not obj.exists():obj.write_bytes(raw[offset:offset+m['size']])
                if sha(obj)!=content:raise ContextError('Content object changed')
                c.execute('INSERT OR IGNORE INTO payload_contents VALUES(?,?,?,?)',(content_id,m['size'],content,str(obj.relative_to(root))))
                c.execute('INSERT OR IGNORE INTO payload_occurrences VALUES(?,?,?,?,?)',(digest('payload',range_id),range_id,content_id,'ELF symbol size','raw named data; no inferred type'))
        resolution=resolutions[ident]
        c.execute('INSERT INTO symbol_occurrences VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(occurrence,ident,anchor,elfsha,m['mangled'],m['demangled'],m['kind'],m.get('binding'),str(section),m['address'],m['size'],range_id,resolution['strategy'],resolution['provider_id'],resolution['binding_status'],resolution['evidence_json']))
        scheme='itanium' if m['mangled'].startswith('_Z') else 'elf-exact-name'
        sig=digest(scheme,abi,m['mangled'])
        c.execute('INSERT OR IGNORE INTO signature_groups VALUES(?,?,?,?,?,0)',(sig,scheme,abi,m['mangled'],int(scheme=='itanium')))
        c.execute('INSERT INTO signature_members VALUES(?,?)',(sig,occurrence))
        if node['kind']=='NativeFunction' and b and b['bytes_sha256']:
            code=digest(elf['e_machine'],elf.elfclass,elf.little_endian,mode,m['size'],b['bytes_sha256'])
            c.execute('INSERT OR IGNORE INTO code_content_groups VALUES(?,?,?,?,?,?,?)',(code,elf['e_machine'],elf.elfclass,'little' if elf.little_endian else 'big',mode,m['size'],b['bytes_sha256']))
            c.execute('INSERT INTO code_content_members VALUES(?,?)',(code,occurrence))
    if len(catalog)!=c.execute('SELECT count(*) FROM symbol_occurrences').fetchone()[0]:raise ContextError('Catalog occurrence loss')
    def reconstruction_kind(members):
        return 'review_existing_result' if any((r['elf_sha256'],r['original_mangled']) in existing_cpp for r in c.execute('SELECT elf_sha256,original_mangled FROM symbol_occurrences WHERE id IN ('+','.join('?'*len(members))+')',members)) else 'reconstruct'
    # Indexed interval lookup preserves overlapping symbol-sized payloads.
    intervals=collections.defaultdict(list)
    for r in c.execute('SELECT p.content_id,r.elf_sha256,r.address,r.size FROM payload_occurrences p JOIN binary_ranges r ON r.id=p.range_id'):
        intervals[r['elf_sha256']].append(dict(r))
    interval_keys={};interval_ends={}
    for elf,rows in intervals.items():
        rows.sort(key=lambda r:r['address']);interval_keys[elf]=[r['address'] for r in rows]
        end=0;ends=[]
        for r in rows:end=max(end,r['address']+r['size']);ends.append(end)
        interval_ends[elf]=ends
    def payloads_at(elf,address):
        if address is None:return []
        rows=intervals[elf];ends=interval_ends[elf];index=bisect.bisect_right(interval_keys[elf],address)-1;found=[]
        while index>=0 and ends[index]>address:
            if rows[index]['address']<=address<rows[index]['address']+rows[index]['size']:found.append(rows[index])
            index-=1
        return found
    # Full symbol-sized payloads only; anonymous previews never become contents.
    edges=collections.defaultdict(list)
    for edge in native.execute('SELECT * FROM edges WHERE kind!="ELF_NAME_CORRESPONDENCE"'):
        edges[edge['src']].append(dict(edge))
    for native_id,members in native_to_occ.items():
        node=all_nodes[native_id];m=json.loads(node['metadata']);b=bodies.get(native_id)
        if node['kind']!='NativeFunction':continue
        raw,elf,sections,mappings,abi,relocs=binaries[node['elf']]
        blockers=[]; obs=[]
        if not b or not b['bytes_sha256']:blockers.append('unknown function range')
        if resolutions[native_id]['strategy']=='external_source':blockers.append('external provider; no firmware reconstruction')
        address=m['address'] & ~1
        instructions=(b or {}).get('instructions',[])
        occupied=set()
        for ins in instructions:
            # The native extractor does not prove arbitrary PC arithmetic,
            # implicit table dispatch, stack-return targets or immediate pointers.
            mnemonic=ins['mnemonic']; operands=ins['operands']
            closed={'mov','mvn','add','sub','rsb','and','orr','eor','bic','lsl','lsr','asr','cmp','cmn','tst','teq'}
            if not (mnemonic=='bx' and operands=='lr') and (mnemonic not in closed or re.search(r'\b(pc|sp)\b|#',operands)):
                blockers.append('instruction outside closed register-arithmetic dependency analysis')
            occupied.update(range(ins['address'],ins['address']+len(bytes.fromhex(ins['bytes']))))
        # Mapping symbols positively identify literal bytes; absent/failed decode
        # is never mistaken for complete coverage.
        mode='a'; mapping_index=0; missing=False
        for a in range(address,address+m['size']):
            while mapping_index<len(mappings) and mappings[mapping_index][0]<=a:
                mode=mappings[mapping_index][1];mapping_index+=1
            if mode!='d' and a not in occupied:missing=True;break
        if missing or not instructions:blockers.append('incomplete instruction coverage')
        for relocation in relocs:
            if address<=relocation['r_offset']<address+m['size']:
                blockers.append('unresolved relocation');obs.append({'relocation':relocation})
        for e in edges[native_id]:
            kind=e['kind']; detail=json.loads(e['metadata']); normalized={'kind':kind,'site_offset':e['site']-address}
            if kind=='ELF_MEMORY_ACCESS':
                normalized['memory']={k:v for k,v in detail.items() if k not in ('elf_sha256','firmware','instruction_address')}
                blockers.append('memory/object semantics require explicit bounded review')
            elif kind in ('ELF_CALLS','ELF_TAIL_BRANCH','ELF_UNRESOLVED'):
                blockers.append('unverified callee/component or indirect dispatch')
                normalized['target_occurrences']=native_to_occ.get(e['dst'],[])
                normalized['detail']=detail
            elif kind in ('ELF_ADDRESS_CANDIDATE','ELF_LITERAL_CELL'):
                target=all_nodes.get(e['dst']); tm=json.loads(target['metadata']) if target else {}
                a=tm.get('address',detail.get('cell_address'))
                rows=payloads_at(node['elf'],a)
                if rows:normalized['payloads']=sorted((r['content_id'],a-r['address']) for r in rows)
                elif kind=='ELF_LITERAL_CELL' and a is not None:
                    sec=next((s for s in sections if s['sh_flags']&2 and s['sh_type']!='SHT_NOBITS' and s['sh_addr']<=a and a+4<=s['sh_addr']+s['sh_size']),None)
                    if sec:normalized['literal_cell_hex']=raw[sec['sh_offset']+a-sec['sh_addr']:sec['sh_offset']+a-sec['sh_addr']+4].hex()
                    else:blockers.append('unmapped literal cell')
                else:blockers.append('address candidate without proven payload extent')
            else:
                normalized['detail']=detail
            obs.append(normalized)
        coverage="complete static instruction ranges" if not missing and instructions else 'incomplete'
        for member in members:
            c.execute('INSERT INTO dependency_observations VALUES(?,?,?,?)',(member,coverage,dump(sorted(obs,key=dump)),dump(sorted(set(blockers)))))
    # Candidate components connect exact signatures OR exact code contents.
    # Union/find is iterative and terminates even for recursive/alias components.
    parents={r[0]:r[0] for r in c.execute('SELECT id FROM symbol_occurrences WHERE strategy="reconstruct" AND symbol_kind="STT_FUNC"')}
    def find(x):
        while parents[x]!=x:parents[x]=parents[parents[x]];x=parents[x]
        return x
    def union(a,b):
        a,b=find(a),find(b)
        if a!=b:parents[max(a,b)]=min(a,b)
    for table in ('signature_members','code_content_members'):
        leaders={}
        for row in c.execute('SELECT group_id,occurrence_id FROM '+table):
            member=row['occurrence_id']
            if member not in parents:continue
            if row['group_id'] in leaders:union(member,leaders[row['group_id']])
            else:leaders[row['group_id']]=member
    grouped=collections.defaultdict(list)
    for member in parents:grouped[find(member)].append(member)
    grouped_members=set()
    for component,members in sorted(grouped.items()):
        if len(members)<2:continue
        members=sorted(members);grouped_members.update(members)
        subject=digest('implementation-candidate',members)
        codes={r[0] for member in members for r in c.execute('SELECT group_id FROM code_content_members WHERE occurrence_id=?',(member,))}
        signatures={r[0] for member in members for r in c.execute('SELECT group_id FROM signature_members WHERE occurrence_id=?',(member,))}
        encoded=all(c.execute('SELECT encoded_signature_equal FROM signature_groups WHERE id=?',(sig,)).fetchone()[0] for sig in signatures)
        if not encoded:
            status,reason='candidate','Unmangled ELF names do not encode parameter interfaces; explicit common-helper review required'
        elif len(codes)!=1 or len(signatures)!=1:
            status,reason='candidate','Different code or encoded interfaces: explicit common-helper/interface review required'
        else:status,reason=evaluate(c,members)
        did=decision(c,subject,'implementation',status,'shared_portable_implementation' if status=='verified' else 'unresolved',reason,members)
        representative=choose(c,members)
        if status=='verified':
            c.execute('INSERT INTO implementation_groups VALUES(?,?,?)',(subject,did,representative))
            c.executemany('INSERT INTO implementation_members VALUES(?,?)',[(subject,x) for x in members])
            add_work(c,reconstruction_kind(members),subject,members,representative,did)
        elif status=='rejected':
            for member in members:add_work(c,reconstruction_kind([member]),member,[member],member,did)
        else:add_work(c,'resolve_equivalence',subject,members,representative,did)
    for row in c.execute('SELECT * FROM symbol_occurrences ORDER BY id').fetchall():
        member=row['id']
        if row['strategy']=='external_source':
            kind='provider_adapter' if row['binding_status']=='adapter_required' else 'provider_binding'
            add_work(c,kind,member,[member],member)
        elif row['symbol_kind']=='STT_FUNC' and member not in grouped_members:
            coverage=c.execute('SELECT blockers FROM dependency_observations WHERE occurrence_id=?',(member,)).fetchone()
            if coverage and 'unknown function range' in json.loads(coverage[0]):
                did=decision(c,member,'range','blocked','unresolved','Unknown function extent; establish boundaries before reconstruction',[member])
                add_work(c,'establish_extent',member,[member],member,did)
            else:add_work(c,reconstruction_kind([member]),member,[member],member)
    for row in c.execute('SELECT id FROM payload_contents').fetchall():
        members=[r[0] for r in c.execute('SELECT o.id FROM symbol_occurrences o JOIN payload_occurrences p ON p.range_id=o.range_id WHERE p.content_id=?',(row['id'],))]
        wid=add_work(c,'extract_payload',row['id'],members,choose(c,members) if members else None)
        # Import already extracted and full-hash checked this shared object.
        c.execute('UPDATE reconstruction_work_items SET status="completed" WHERE id=?',(wid,))
    # Independent exact-byte/content attestations do not imply shared behavior.
    for table,member_table,kind,scope in [('code_content_groups','code_content_members','code','exact_bytes')]:
        for row in c.execute('SELECT id FROM '+table).fetchall():
            members=[r[0] for r in c.execute('SELECT occurrence_id FROM '+member_table+' WHERE group_id=?',(row['id'],))]
            decision(c,row['id'],kind,'verified',scope,'Full exact section-mapped bytes, size and machine context',members)
    for row in c.execute('SELECT id FROM payload_contents').fetchall():
        members=[r[0] for r in c.execute('SELECT id FROM payload_occurrences WHERE content_id=?',(row['id'],))]
        decision(c,row['id'],'payload','verified','exact_payload_content','Full bounded file bytes; no preview comparison',members)
    if any(sha(pathlib.Path(__file__).with_name(name))!=value for name,value in producer_inputs.items()):raise ContextError('Producer changed during import; preserve failed generation')
    c.execute('INSERT INTO index_meta VALUES(?,?)',('complete','true'))
    c.commit()
    if c.execute('PRAGMA foreign_key_check').fetchall():raise ContextError('Foreign key check failed')
    result=report(c);c.close()
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def choose(c,members):
    return min(members,key=lambda x:tuple(c.execute('SELECT CASE WHEN range_id IS NULL THEN 1 ELSE 0 END,CASE WHEN (SELECT coverage FROM dependency_observations WHERE occurrence_id=symbol_occurrences.id)="complete static instruction ranges" THEN 0 ELSE 1 END,elf_sha256,original_address,id FROM symbol_occurrences WHERE id=?',(x,)).fetchone()))


def report(c):
    result={k:c.execute('SELECT count(*) FROM '+table).fetchone()[0] for k,table in [('symbol_occurrences','symbol_occurrences'),('encoded_signatures','signature_groups'),('exact_code_contents','code_content_groups'),('physical_ranges','binary_ranges'),('implementation_groups','implementation_groups'),('payload_contents','payload_contents'),('payload_occurrences','payload_occurrences')]}
    result['exact_name_groups_including_unmangled']=result.pop('encoded_signatures')
    result['encoded_signatures']=c.execute('SELECT count(*) FROM signature_groups WHERE encoded_signature_equal=1').fetchone()[0]
    result['unknown_extent_work_items']=c.execute('SELECT count(*) FROM reconstruction_work_items WHERE work_kind="establish_extent"').fetchone()[0]
    result['external_source_bindings']=c.execute('SELECT count(*) FROM symbol_occurrences WHERE strategy="external_source"').fetchone()[0]
    result['blocked_equivalence_candidates']=c.execute('SELECT count(*) FROM equivalence_decisions d WHERE equivalence_kind="implementation" AND status="blocked" AND revision=(SELECT max(revision) FROM equivalence_decisions WHERE subject_id=d.subject_id)').fetchone()[0]
    result['work_kinds']={r[0]:r[1] for r in c.execute('SELECT work_kind,count(*) FROM reconstruction_work_items WHERE status!="superseded" GROUP BY work_kind')}
    result['issued_reconstruction_work_items']=c.execute('SELECT count(*) FROM work_claims c JOIN reconstruction_work_items w ON w.id=c.work_item_id WHERE w.work_kind="reconstruct"').fetchone()[0]
    result['excluded_duplicate_jobs']=sum(r[0]-1 for r in c.execute('SELECT count(*) FROM work_item_members m JOIN reconstruction_work_items w ON w.id=m.work_item_id JOIN equivalence_decisions d ON d.id=w.decision_id WHERE w.status!="superseded" AND d.status="verified" AND d.verification_scope="shared_portable_implementation" GROUP BY w.id HAVING count(*)>1'))
    result['excluded_payload_extractions']=c.execute('SELECT count(*) FROM payload_occurrences').fetchone()[0]-c.execute('SELECT count(*) FROM payload_contents').fetchone()[0]
    result['deferred_candidate_duplicates']=sum(r[0]-1 for r in c.execute('SELECT count(*) FROM work_item_members m JOIN reconstruction_work_items w ON w.id=m.work_item_id WHERE w.status!="superseded" AND w.work_kind="resolve_equivalence" GROUP BY w.id'))
    result['generation']=meta(c,'generation')
    result['candidate_equivalence_groups']=c.execute('SELECT count(*) FROM reconstruction_work_items WHERE work_kind="resolve_equivalence" AND status!="superseded"').fetchone()[0]
    result['completed_payload_extractions']=c.execute('SELECT count(*) FROM reconstruction_work_items WHERE work_kind="extract_payload" AND status="completed"').fetchone()[0]
    return result


def verify_inputs(c,root=ROOT):
    if not meta(c,'complete'):raise ContextError('Incomplete index')
    pointer=json.loads((root/'dependency-graph/NATIVE_ACTIVE.json').read_text())
    if sha(inside(root,pointer['database']))!=pointer['sha256'] or sha(inside(root,pointer['report']))!=pointer['report_sha256']:raise ContextError('Native database/report changed')
    if pointer['sha256']!=meta(c,'native_generation'):raise ContextError('Native generation changed; import a new dedup index')
    if any(sha(inside(root,name))!=value for name,value in meta(c,'release_inputs').items()):raise ContextError('Additional release input changed')
    if any(sha(pathlib.Path(__file__).with_name(name))!=value for name,value in meta(c,'producer_inputs').items()):raise ContextError('Dedup producer changed; import a new generation')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('import','report','plan','claim','release','complete','review','publish'))
    p.add_argument('--release-manifest',action='append',default=[])
    p.add_argument('--out');p.add_argument('--db');p.add_argument('--task');p.add_argument('--owner');p.add_argument('--packet');p.add_argument('--claim');p.add_argument('--manifest')
    a=p.parse_args()
    if a.action=='import':
        native,pointer=open_index(ROOT)
        try:print(json.dumps(build(native,pointer,inside(ROOT,a.out),releases=[inside(ROOT,p) for p in a.release_manifest]),indent=2))
        finally:native.close()
    else:
        lock_stream=None
        if a.action in ('claim','review','release','complete','publish'):
            import fcntl
            lock_path=ROOT/'dependency-graph/state/context.lock'
            lock_path.parent.mkdir(parents=True,exist_ok=True)
            lock_stream=lock_path.open('a');fcntl.flock(lock_stream,fcntl.LOCK_EX)
        from dedup_work import plan,claim,transition,review,publish
        if a.action=='publish':
            print(json.dumps(publish(ROOT,inside(ROOT,a.db)),indent=2));return
        with connect(inside(ROOT,a.db)) as c:
            if a.action=='report':result=report(c)
            elif a.action=='plan':result=plan(c,json.loads(inside(ROOT,a.task).read_text()))
            elif a.action=='claim':result=claim(c,json.loads(inside(ROOT,a.task).read_text()),a.owner,a.packet)
            elif a.action=='review':result=review(c,json.loads(inside(ROOT,a.manifest).read_text()))
            else:result=transition(c,a.claim,a.action,json.loads(inside(ROOT,a.manifest).read_text()))
            print(json.dumps(result,indent=2))


if __name__=='__main__':
    try:main()
    except (ContextError,ValueError,KeyError) as e:raise SystemExit('DEDUP BLOCKED: '+str(e))
