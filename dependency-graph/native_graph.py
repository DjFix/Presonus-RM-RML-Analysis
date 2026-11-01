"""Offline, hash-bound ARM ELF observations. No inferred C++ declarations."""
import argparse
import bisect
import hashlib
import io
import json
import pathlib
import sqlite3
import struct
import subprocess
import time

from context_runtime import ContextError, sha

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = ROOT / 'dependency-graph'


def key(elf, name, address, size, section):
    text = json.dumps([elf, name, address, size, section], separators=(',', ':'))
    return 'native:' + hashlib.sha256(text.encode()).hexdigest()


def byte_address(address, kind):
    return address & ~1 if kind=='STT_FUNC' else address


def build(out, manifests=None):
    from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM, CS_MODE_THUMB, CS_MODE_LITTLE_ENDIAN, CS_GRP_CALL, CS_GRP_JUMP
    from capstone.arm import ARM_OP_IMM, ARM_OP_REG, ARM_OP_MEM, ARM_REG_PC, ARM_REG_LR
    from elftools.elf.elffile import ELFFile
    active = json.loads((ROOT/'uc-library/validation/registry-sqlite/ACTIVE.json').read_text())
    registry = sqlite3.connect(pathlib.Path(active['database']['absolute_path']).as_uri()+'?mode=ro', uri=True)
    registry.row_factory = sqlite3.Row
    out.mkdir(parents=True, exist_ok=False)
    c = sqlite3.connect(out/'native.sqlite')
    c.executescript('''CREATE TABLE binaries(id TEXT PRIMARY KEY,firmware TEXT,role TEXT,path TEXT,metadata TEXT);
      CREATE TABLE nodes(id TEXT PRIMARY KEY,kind TEXT,label TEXT,elf TEXT,metadata TEXT);
      CREATE TABLE edges(src TEXT,dst TEXT,kind TEXT,site INTEGER,metadata TEXT,PRIMARY KEY(src,dst,kind,site));
      CREATE INDEX edge_dst ON edges(dst,kind); CREATE INDEX edge_src ON edges(src,kind);
      CREATE TABLE bodies(id TEXT PRIMARY KEY,payload TEXT);
      CREATE INDEX nodes_elf ON nodes(elf);
      CREATE TABLE inputs(path TEXT PRIMARY KEY,sha256 TEXT);''')
    c.executescript('''CREATE TABLE providers(id TEXT PRIMARY KEY,pinned_commit TEXT,source_root TEXT,repository TEXT,policy_json TEXT);
      CREATE TABLE symbol_resolution(symbol_id TEXT PRIMARY KEY,strategy TEXT,provider_id TEXT,binding_status TEXT,evidence_json TEXT);''')
    provider='ccl-core';source_root=ROOT/'third_party/ccl-framework'
    pin='e8cbdea4a4a20e15111f5a690798a259c0374b31'
    if subprocess.check_output(['git','-C',str(source_root),'rev-parse','HEAD'],text=True).strip()!=pin:
        raise ContextError('CCL checkout is not pinned to the approved commit')
    if subprocess.check_output(['git','-C',str(source_root),'status','--porcelain','--untracked-files=no'],text=True).strip():
        raise ContextError('Official CCL tracked files modified; do not bless external-source bindings')
    c.execute('INSERT INTO providers VALUES(?,?,?,?,?)',(provider,pin,str(source_root.relative_to(ROOT)),
       'https://github.com/cclsoftware/ccl-framework',json.dumps({'binary_reconstruction_allowed':False,'original_arm_abi_verified':False})))
    source_maps={}
    for role in ('client','server'):
        file=ROOT/'uc-library/validation/core-upstream/source-map'/f'{role}-functions.json'
        mapping=json.loads(file.read_text())
        if mapping['commit']!=pin:raise ContextError('Source-map commit mismatch')
        c.execute('INSERT INTO inputs VALUES(?,?)',(str(file.relative_to(ROOT)),sha(file)))
        for row in mapping['functions']:
            source_maps[(row['original_elf_sha256'],row['mangled'],row['address'],row['size'])]=row
    def node(k, kind, label, elf, meta):
        c.execute('INSERT OR IGNORE INTO nodes VALUES(?,?,?,?,?)', (k,kind,label,elf,json.dumps(meta,sort_keys=True)))
        return k
    def edge(s,d,k,site,meta):
        c.execute('INSERT OR IGNORE INTO edges VALUES(?,?,?,?,?)',(s,d,k,site,json.dumps(meta,sort_keys=True)))
    producer_digest=sha(pathlib.Path(__file__))
    decoders={m:Cs(CS_ARCH_ARM, flag|CS_MODE_LITTLE_ENDIAN) for m,flag in [('a',CS_MODE_ARM),('t',CS_MODE_THUMB)]}
    for decoder in decoders.values():decoder.detail=True
    started = time.perf_counter(); counts = []
    manifest_paths=manifests or [ROOT/'uc-library/recovered-all'/role/'manifest.json' for role in ('client','server')]
    seen_elf=set()
    for manifest_path in manifest_paths:
        manifest_path=pathlib.Path(manifest_path).resolve()
        if not manifest_path.is_relative_to(ROOT):raise ContextError('ELF export manifest must be repository-local')
        folder=manifest_path.parent
        manifest = json.loads(manifest_path.read_text())
        elfsha = manifest['sha256']; path = ROOT/manifest['path']; raw = path.read_bytes()
        if elfsha in seen_elf:continue
        seen_elf.add(elfsha)
        if hashlib.sha256(raw).hexdigest()!=elfsha: raise ContextError('ELF identity mismatch: '+str(path))
        elf = ELFFile(io.BytesIO(raw)); sections = list(elf.iter_sections())
        if elf['e_machine']!='EM_ARM' or not elf.little_endian: raise ContextError('Unsupported ELF architecture')
        originals = [dict(r) for r in registry.execute('SELECT * FROM catalog_symbols WHERE elf=?',(elfsha,))]
        roles=sorted({r['role'] for r in originals})
        if len(roles)!=1:raise ContextError('Missing/ambiguous catalog role for ELF')
        role=roles[0]
        versions = sorted({r['firmware'] for r in originals})
        if len(versions)!=1: raise ContextError('Missing/ambiguous firmware identity')
        firmware=versions[0]
        c.execute('INSERT INTO binaries VALUES(?,?,?,?,?)',(elfsha,firmware,role,manifest['path'],json.dumps(manifest)))
        for file in (path,manifest_path):
            c.execute('INSERT INTO inputs VALUES(?,?)',(str(file.relative_to(ROOT)),sha(file)))
        real = list(elf.get_section_by_name('.symtab').iter_symbols())
        identities={(s.name,s['st_value'],s['st_size'],s['st_shndx']) for s in real}
        by_address={}; entries={}; objects=[]; functions=[]
        for r in originals:
            section=json.loads(r['section_json']); identity=(r['mangled'],r['address'],r['size'],section)
            if identity not in identities: raise ContextError('Catalog identity absent from source ELF: '+str(identity))
            k=key(elfsha,*identity); core=r['policy'].startswith('core-')
            meta=dict(r,elf_sha256=elfsha,firmware=firmware,section=section,core_source_boundary=core)
            kind='NativeFunction' if r['kind']=='STT_FUNC' else 'NativeData'
            node(k,kind,r['demangled'],elfsha,meta);entries[k]=meta
            mapping=source_maps.get((elfsha,r['mangled'],r['address'],r['size']))
            binding={'original_declaration_verified':False,'original_arm_abi_verified':False,
                     'binary_behavior_verified':False,'upstream':[]}
            state='unmatched'
            if core and mapping:
                binding.update(source_map_status=mapping.get('status'),
                    exact_encoded_interface_match=mapping.get('exact_encoded_interface_match',False))
                for source in mapping.get('upstream',[]):
                    source_file=source_root/source['path']
                    if source_file.is_file():
                        digest=sha(source_file)
                        c.execute('INSERT OR IGNORE INTO inputs VALUES(?,?)',(str(source_file.relative_to(ROOT)),digest))
                        binding['upstream'].append(dict(source,repository_path=str(source_file.relative_to(ROOT)),sha256=digest))
                if binding['upstream']:
                    state='verified' if mapping.get('exact_encoded_interface_match') else 'candidate'
                if 'different mangling' in mapping.get('status','') or 'adapt' in mapping.get('status','').lower():state='adapter_required'
                binding['verification_scope']='pinned source and encoded interface only; not original return/layout/behavior'
            c.execute('INSERT OR IGNORE INTO symbol_resolution VALUES(?,?,?,?,?)',
                (k,'external_source' if core else 'reconstruct',provider if core else None,state,json.dumps(binding)))
            by_address.setdefault(byte_address(r['address'],r['kind']),[]).append(k)
            (functions if kind=='NativeFunction' else objects).append(k)
        function_set=set(functions)
        function_addresses={a:[k for k in keys if k in function_set] for a,keys in by_address.items()}
        mapped=[]
        for s in real:
            if s.name.split('.')[0] in ('$a','$t','$d'):
                mapped.append((s['st_value'],s.name[1]))
        mapped.sort(); starts=[a for a,_ in mapped]
        def mode_at(address):
            i=bisect.bisect_right(starts,address)-1
            return mapped[i][1] if i>=0 else 'a'
        def read(address,size):
            for sec in sections:
                if sec['sh_addr']<=address and address+size<=sec['sh_addr']+sec['sh_size'] and sec['sh_flags']&2:
                    if sec['sh_type']=='SHT_NOBITS': return None,sec,None
                    offset=sec['sh_offset']+address-sec['sh_addr'];return raw[offset:offset+size],sec,offset
            return None,None,None
        def address_node(address):
            if address in by_address:return by_address[address]
            if address&1 and function_addresses.get(address & ~1):return function_addresses[address & ~1]
            data,sec,offset=read(address,1)
            k=f'native-address:{elfsha}:{address:x}'
            node(k,'NativeAddress',hex(address),elfsha,{'elf_sha256':elfsha,'firmware':firmware,
                 'address':address,'section':sec.name if sec else None,'file_offset':offset,
                 'preview_range_size':min(256,sec['sh_addr']+sec['sh_size']-address) if sec and offset is not None else 0,
                 'mapped':sec is not None,'interpretation':'address candidate, not a proven object/type'})
            return [k]
        # Actual symbol ranges, including data pools and NOBITS, are checked separately.
        for k,meta in entries.items():
            section=meta['section']; size=meta['size']; address=byte_address(meta['address'],meta['kind'])
            if not isinstance(section,int) or not size: continue
            sec=sections[section]
            if address<sec['sh_addr'] or address+size>sec['sh_addr']+sec['sh_size']:
                raise ContextError('Symbol range crosses actual ELF section')
            data=None if sec['sh_type']=='SHT_NOBITS' else raw[sec['sh_offset']+address-sec['sh_addr']:sec['sh_offset']+address-sec['sh_addr']+size]
            body={'address':meta['address'],'size':size,'section':sec.name,'section_index':section,
                  'file_offset':None if data is None else sec['sh_offset']+address-sec['sh_addr'],
                  'bytes_sha256':None if data is None else hashlib.sha256(data).hexdigest(),
                  'storage':'NOBITS' if data is None else 'file','instructions':[], 'coverage':'data or Core boundary'}
            if k in function_set and not meta['core_source_boundary'] and data is not None:
                instructions=[];offset=0; register_values={}
                while offset<len(data):
                    address_here=address+offset; mode=mode_at(address_here)
                    step=2 if mode=='t' else 4
                    if mode=='d':offset+=step;continue
                    cs=decoders['t' if mode=='t' else 'a']
                    ins=next(cs.disasm(data[offset:offset+4],address_here,count=1),None)
                    if not ins:
                        edge(k,k,'ELF_UNRESOLVED',address_here,{'reason':'instruction decode failed'});offset+=step;continue
                    instructions.append({'address':ins.address,'bytes':ins.bytes.hex(),'mnemonic':ins.mnemonic,'operands':ins.op_str})
                    ops=ins.operands; mnemonic=ins.mnemonic; target=None
                    is_call=ins.group(CS_GRP_CALL)
                    if is_call and ops and ops[0].type==ARM_OP_IMM:
                        target=ops[0].imm & ~1
                        for dest in address_node(target):edge(k,dest,'ELF_CALLS',ins.address,{'instruction':mnemonic,'target_address':target})
                    elif is_call or (mnemonic.startswith('bx') and ops and ops[0].type==ARM_OP_REG and ops[0].reg!=ARM_REG_LR):
                        edge(k,k,'ELF_UNRESOLVED',ins.address,{'reason':'indirect dispatch','instruction':mnemonic,'operands':ins.op_str})
                    elif ins.group(CS_GRP_JUMP) and ops and ops[0].type==ARM_OP_IMM:
                        target=ops[0].imm & ~1
                        if not address<=target<address+size:
                            for dest in address_node(target):edge(k,dest,'ELF_TAIL_BRANCH',ins.address,{'instruction':mnemonic,'target_address':target,'classification':'external branch candidate'})
                    # PC-relative literal loads: preserve literal cell and its value separately.
                    for operand in ops:
                        if operand.type==ARM_OP_MEM and operand.mem.base!=ARM_REG_PC:
                            ident=f'native-memory:{elfsha}:{ins.address:x}'
                            detail={'elf_sha256':elfsha,'firmware':firmware,'instruction_address':ins.address,
                                'base_register':ins.reg_name(operand.mem.base),'index_register':ins.reg_name(operand.mem.index),
                                'displacement':operand.mem.disp,'scale':operand.mem.scale,
                                'shift_type':operand.shift.type,'shift_value':operand.shift.value,
                                'instruction':mnemonic,'operands':ins.op_str,
                                'interpretation':'observed explicit memory operand; original class fields/types/ownership unresolved'}
                            node(ident,'NativeMemoryAccess',ins.op_str,elfsha,detail)
                            edge(k,ident,'ELF_MEMORY_ACCESS',ins.address,detail)
                        if operand.type==ARM_OP_MEM and operand.mem.base==ARM_REG_PC:
                            cell=((ins.address+(4 if mode=='t' else 8)) & ~3)+operand.mem.disp
                            literal,ls,lo=read(cell,4)
                            if literal is not None:
                                value=struct.unpack('<I',literal)[0]
                                for dest in address_node(cell):edge(k,dest,'ELF_LITERAL_CELL',ins.address,{'cell_address':cell,'value':value,'instruction':mnemonic})
                                _,vs,_=read(value,1)
                                if vs and mnemonic.startswith('ldr') and not mnemonic.startswith(('ldrb','ldrh','ldrsb','ldrsh')):
                                    for dest in address_node(value):edge(k,dest,'ELF_ADDRESS_CANDIDATE',ins.address,{'literal_address':cell,'value':value,'certainty':'inferred address, may be scalar'})
                    offset+=ins.size
                body.update(instructions=instructions,coverage='static decoded instruction ranges; indirect dispatch explicit')
                pseudo=folder/'pseudocode'/f'{meta["address"]:08x}.cpp.txt'
                export=folder/'machine-code'/f'{meta["address"]:08x}-{size:x}.bin'
                if export.exists() and export.read_bytes()!=data:raise ContextError('Export bytes mismatch')
                if pseudo.exists():body['pseudocode_path']=str(pseudo.relative_to(ROOT));body['pseudocode_sha256']=sha(pseudo)
            c.execute('INSERT OR REPLACE INTO bodies VALUES(?,?)',(k,json.dumps(body)))
        # Scan named data objects, including vtables, for exact function-pointer words.
        for k in objects:
            m=entries[k];data,sec,off=read(m['address'],m['size']) if m['size'] else (None,None,None)
            if data is None:continue
            for i in range(0,len(data)-3,4):
                value=struct.unpack_from('<I',data,i)[0]
                for dest in by_address.get(value & ~1,[]):
                    if dest in function_set:
                        edge(k,dest,'ELF_TABLE_FUNCTION' if m['mangled'].startswith('_ZTV') else 'ELF_POINTER_CANDIDATE',m['address']+i,
                             {'slot_offset':i,'word':value,'certainty':'observed word equals function address; dispatch not proven'})
        c.commit();counts.append({'elf':elfsha,'firmware':firmware,'role':role,'symbols':len(entries)})
        print(json.dumps(counts[-1]),flush=True)
    # Cross-binary/version name matches are correspondences, never call edges.
    names={}
    for k,elf,meta in c.execute('SELECT id,elf,metadata FROM nodes WHERE kind="NativeFunction"'):
        name=json.loads(meta)['mangled'];names.setdefault(name,[]).append((k,elf))
    for name,items in names.items():
        for s,se in items:
            for d,de in items:
                if se!=de:edge(s,d,'ELF_NAME_CORRESPONDENCE',-1,{'basis':'exact mangled name only','abi_or_behavior_equivalence':False})
    c.commit();report={'version':1,'binaries':counts,'seconds':time.perf_counter()-started,
        'nodes':c.execute('SELECT count(*) FROM nodes').fetchone()[0],'edges':c.execute('SELECT count(*) FROM edges').fetchone()[0],
        'producer_sha256':producer_digest,'runtime_complete':False}
    if sha(pathlib.Path(__file__))!=producer_digest:raise ContextError('Producer changed while indexing')
    c.close();registry.close();report['database_sha256']=sha(out/'native.sqlite')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    pointer={'database':str((out/'native.sqlite').relative_to(ROOT)),'sha256':report['database_sha256'],
             'report':str((out/'report.json').relative_to(ROOT)),'report_sha256':sha(out/'report.json')}
    temp=BASE/'NATIVE_ACTIVE.new';temp.write_text(json.dumps(pointer,indent=2)+'\n');temp.replace(BASE/'NATIVE_ACTIVE.json')
    print(json.dumps(report),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True)
    p.add_argument('--manifest',action='append',type=pathlib.Path,help='Repeat for every role/version to retain in this index; defaults to current client/server')
    a=p.parse_args();build(ROOT/a.out,a.manifest)
