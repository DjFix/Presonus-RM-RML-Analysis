"""Small native evidence packets from immutable, per-ELF SQLite observations."""
import hashlib
import json
import pathlib
import sqlite3
import struct

from context_runtime import ContextError, inside, sha
from native_graph import key

KINDS = ('ELF_CALLS','ELF_TAIL_BRANCH','ELF_LITERAL_CELL','ELF_ADDRESS_CANDIDATE',
         'ELF_TABLE_FUNCTION','ELF_POINTER_CANDIDATE','ELF_UNRESOLVED','ELF_MEMORY_ACCESS')


def open_index(root):
    pointer_path=root/'dependency-graph/NATIVE_ACTIVE.json'
    if not pointer_path.is_file():raise ContextError('Native index absent; empty packets are forbidden')
    pointer=json.loads(pointer_path.read_text());db=inside(root,pointer['database'])
    if sha(db)!=pointer['sha256'] or sha(inside(root,pointer['report']))!=pointer['report_sha256']:
        raise ContextError('Native index generation hash mismatch')
    c=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row
    for row in c.execute('SELECT * FROM inputs'):
        if sha(inside(root,row['path']))!=row['sha256']:raise ContextError('Native input changed: '+row['path'])
    return c,pointer


def target_key(original):
    return key(original['elf'],original['mangled'],original['address'],original['size'],json.loads(original['section_json']))


def select(c, seeds, query=None):
    nodes={};edges=[]
    for seed in seeds:
        rows=c.execute('SELECT * FROM edges WHERE (src=? OR dst=?) AND kind!=?',(seed,seed,'ELF_NAME_CORRESPONDENCE')).fetchall()
        if query=='callees':rows=[r for r in rows if r['src']==seed and r['kind'] in ('ELF_CALLS','ELF_TAIL_BRANCH')]
        elif query=='callers':rows=[r for r in rows if r['dst']==seed and r['kind'] in ('ELF_CALLS','ELF_TAIL_BRANCH')]
        elif query=='references':rows=[r for r in rows if r['dst']==seed]
        elif query not in (None,'native_body','native_data'):raise ContextError('Unsupported native query: '+str(query))
        edges.extend(dict(row) for row in rows)
    ids=set(seeds)|{e['src'] for e in edges}|{e['dst'] for e in edges}
    for ident in sorted(ids):
        row=c.execute('SELECT * FROM nodes WHERE id=?',(ident,)).fetchone()
        if not row:raise ContextError('Missing native graph endpoint: '+ident)
        nodes[ident]={'kind':row['kind'],'label':row['label'],'elf':row['elf'],'metadata':json.loads(row['metadata'])}
        binding=c.execute('SELECT * FROM symbol_resolution WHERE symbol_id=?',(ident,)).fetchone()
        if binding:
            binding=dict(binding);binding['evidence']=json.loads(binding.pop('evidence_json'))
            if binding['provider_id']:
                provider=c.execute('SELECT * FROM providers WHERE id=?',(binding['provider_id'],)).fetchone()
                binding['provider']=dict(provider)
            nodes[ident]['resolution']=binding
    # No cross-ELF execution edges are allowed, including aliases.
    for e in edges:
        if nodes[e['src']]['elf']!=nodes[e['dst']]['elf']:raise ContextError('Cross-ELF execution edge')
        e['metadata']=json.loads(e['metadata'])
    return nodes,edges


def make_context(root, out, originals, required=True):
    c,pointer=open_index(root)
    try:
        seeds=[target_key(item['original']) for item in originals]
        nodes,edges=select(c,seeds); bodies={};external_bodies={};selected={}; elf_bytes={}; binaries={}
        for item,seed in zip(originals,seeds):
            original=item['original'];meta=nodes[seed]['metadata']
            if any(meta.get(field)!=original.get(field) for field in ('elf','firmware','role','mangled','address','size','section_json')):
                raise ContextError('Requested ELF/version/range differs from native index')
        for row in c.execute('SELECT * FROM binaries'):
            binaries[row['id']]=dict(row)
        for seed in seeds:
            meta=nodes[seed]['metadata']
            row=c.execute('SELECT payload FROM bodies WHERE id=?',(seed,)).fetchone()
            body=json.loads(row[0]) if row else None
            if not body or not body['instructions']:
                continue
            bodies[seed]=body
        # Root full bodies; one-hop neighbors are summaries, not recursively expanded bundles.
        data={}
        for ident,value in nodes.items():
            meta=value['metadata']; elf=value['elf']; binary=binaries[elf]
            file=inside(root,binary['path'])
            binding=value.get('resolution',{})
            for source in binding.get('evidence',{}).get('upstream',[]):
                selected[source['repository_path']]=source['sha256']
                if ident in seeds and binding.get('binding_status')=='verified' and source.get('definition'):
                    raw_source=inside(root,source['repository_path']).read_bytes()
                    start,end=source.get('definition_extent_start'),source.get('definition_extent_end')
                    if start is not None and end is not None:
                        excerpt=raw_source[start:end]
                        if sha(inside(root,source['repository_path']))!=source['sha256'] or hashlib.sha256(excerpt).hexdigest()!=source['definition_extent_sha256']:
                            raise ContextError('Upstream definition extent differs from pinned source-map')
                        external_bodies.setdefault(ident,[]).append({'path':source['repository_path'],'source_sha256':source['sha256'],
                            'excerpt':excerpt.decode('utf-8'),'provider':binding['provider'],'scope':'pinned external implementation; not firmware behavior/ABI'})
            if elf not in elf_bytes:
                raw=file.read_bytes()
                if hashlib.sha256(raw).hexdigest()!=elf:raise ContextError('ELF bytes changed')
                elf_bytes[elf]=raw;selected[binary['path']]=elf
            body_row=c.execute('SELECT payload FROM bodies WHERE id=?',(ident,)).fetchone()
            b=json.loads(body_row[0]) if body_row else None
            if ident in bodies:
                off=b['file_offset']; payload=elf_bytes[elf][off:off+b['size']]
                if hashlib.sha256(payload).hexdigest()!=b['bytes_sha256']:raise ContextError('Target byte range hash mismatch')
                pseudo=b.get('pseudocode_path')
                if pseudo:
                    if sha(inside(root,pseudo))!=b['pseudocode_sha256']:raise ContextError('Pseudocode changed since indexing')
                    selected[pseudo]=b['pseudocode_sha256'];bodies[ident]['unvalidated_pseudocode']=inside(root,pseudo).read_text()
            elif value['kind'] in ('NativeData','NativeAddress'):
                off=(b or meta).get('file_offset');size=(b or meta).get('size',64)
                # Anonymous addresses only have a four-byte section-checked location.
                if b is None:size=meta.get('preview_range_size',4)
                if off is not None:
                    count=min(size,256);payload=elf_bytes[elf][off:off+count]
                    data[ident]={'address':meta['address'],'original_size':size,'preview_bytes':count,
                        'preview_hex':payload.hex(),'truncated':count<size,
                        'words_u32':list(struct.unpack('<'+'I'*(len(payload)//4),payload[:len(payload)//4*4])),
                        'full_range_sha256':(b or {}).get('bytes_sha256'),
                        'interpretation':'raw data/table words; not original declared type/layout'}
                else:data[ident]={'storage':(b or {}).get('storage','unknown'),'bytes_available':False}
        if required and any(seed not in bodies and seed not in external_bodies for seed in seeds):
            raise ContextError('No verified native/pinned upstream body; empty context forbidden')
        selected[pointer['database']]=pointer['sha256'];selected[pointer['report']]=pointer['report_sha256']
        result={'version':1,'generation_sha256':pointer['sha256'],'roots':seeds,'nodes':nodes,'external_bodies':external_bodies,
                'edges':edges,'bodies':bodies,'data':data,'binaries':{e:binaries[e] for e in {v['elf'] for v in nodes.values()}},
                'selected_file_sha256':selected,
                'policy':{'hops':1,'neighbors':'identities and typed relations; request body expansion explicitly',
                          'runtime_complete':False,'unvalidated_pseudocode':True,'cross_version_names_are_not_calls':True}}
        (out/'native-context.json').write_text(json.dumps(result,indent=2)+'\n')
        lines=['# ELF context','', 'Full target ranges verified against exact source ELF. Static evidence; C++ return/layout remains unresolved.',
               'One-hop calls/references only. Neighbor bodies require explicit expansion. Pseudocode is unvalidated.','']
        for ident,body in bodies.items():
            meta=nodes[ident]['metadata'];lines+=['## '+meta['demangled'],'',
              f"ELF `{meta['elf_sha256']}`; version `{meta['firmware']}`; `{meta['role']}`; original `{meta['mangled']}`; address `{meta['address']:#x}`; size {meta['size']}; section {body['section']}; SHA256 `{body['bytes_sha256']}`",
              f"Original ELF path: `{binaries[meta['elf']]['path']}`; file offset `{body['file_offset']:#x}`. Exact full range is offset + size; includes any literal pool bytes.",'','```asm']
            lines += [f"{i['address']:08x}  {i['bytes']}  {i['mnemonic']} {i['operands']}" for i in body['instructions']]
            lines+=['```','']
            if body.get('unvalidated_pseudocode'):lines+=['### Unvalidated pseudocode — declarations are not evidence','','```text',body['unvalidated_pseudocode'],'```','']
        lines+=['## Typed relationships','']
        for e in edges:lines.append(f"- {e['kind']}: `{nodes[e['src']]['label']}` → `{nodes[e['dst']]['label']}` at {e['site']:#x}; {json.dumps(e['metadata'])}")
        lines+=['','## External-source bindings — do not reconstruct these providers from firmware','']
        for ident,value in nodes.items():
            binding=value.get('resolution',{})
            if binding.get('strategy')=='external_source':
                lines += ['- `'+ident+'`: '+json.dumps(binding,ensure_ascii=False)]
        for ident,entries in external_bodies.items():
            for entry in entries:lines+=['','### Pinned upstream definition for '+ident,'',entry['path'],'','```cpp',entry['excerpt'],'```']
        lines+=['','## Bound raw data','',json.dumps(data,indent=2),'']
        (out/'ELF_CONTEXT.md').write_text('\n'.join(lines))
        return result
    finally:c.close()


def require_nonempty(packet):
    native=packet.get('native_context',{})
    source=packet.get('source_slices',{}).get('functions',{})
    native_bodies={k:v for k,v in native.get('bodies',{}).items() if v.get('instructions') and
                   len(v.get('bytes_sha256',''))==64 and v.get('size',0)>0 and v.get('file_offset') is not None}
    source_bodies={k:v for k,v in source.items() if v.get('excerpt','').strip() and len(v.get('source_sha256',''))==64}
    external_bodies={k:entries for k,entries in native.get('external_bodies',{}).items() if any(e.get('excerpt','').strip() and len(e.get('source_sha256',''))==64 for e in entries)}
    if not native_bodies and not source_bodies and not external_bodies:
        raise ContextError('Empty evidence packet forbidden for every mode, including research')
    for item in packet['originals']:
        name=item['original']['mangled']; ident=target_key(item['original'])
        if ident not in native_bodies and ident not in external_bodies and not any(v.get('mangled')==name for v in source_bodies.values()):
            raise ContextError('Target has no usable body: '+name)
