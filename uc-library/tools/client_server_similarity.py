#!/usr/bin/env python3
"""Read-only comparison of existing client/server symbols and non-Core exports.

Fingerprints are candidate selectors, never source/behavior/ABI verification.
No decompiler, emulator, firmware operation or Core-body analysis is performed.
"""
import argparse
from bisect import bisect_right
from collections import Counter, defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import sys

import capstone
from elftools.elf.elffile import ELFFile
from extraction_verify_bounded import owning_namespace


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    return sha(path.read_bytes())


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def defined(row):
    return row['kind'] == 'STT_FUNC' and bool(row['size']) and isinstance(row['section'], int)


def category(row):
    owner = owning_namespace(row['mangled'])
    name = row['demangled']
    if owner == 'Presonus':
        return 'Presonus application'
    if owner == 'Core' or name.startswith(('global constructors keyed to Core::','global destructors keyed to Core::')):
        return 'Core source provider'
    if owner == 'std' or name.startswith(('std::', '__', '_Unwind', 'operator ')):
        return 'C++ or compiler runtime'
    return 'Other named C/C++ (ownership not inferred)'


def namespace(row):
    if category(row) == 'Presonus application':
        match = re.search(r'Presonus::([A-Za-z_][A-Za-z_0-9]*)::', row['demangled'])
        return 'Presonus::' + match[1] if match else 'Presonus (direct members)'
    return category(row)


class AddressNames:
    def __init__(self, rows, common):
        groups = defaultdict(list)
        self.objects = []
        for row in rows:
            if isinstance(row['section'], int) and row['address']:
                groups[row['address']].append(row['mangled'])
        self.names = {a: sorted(set(names), key=lambda n: (n not in common, n))[0]
                      for a, names in groups.items()}
        for row in rows:
            if row['kind'] == 'STT_OBJECT' and row['size'] and isinstance(row['section'], int):
                self.objects.append((row['address'], row['address'] + row['size'], self.names[row['address']]))
        self.objects.sort()
        self.starts = [r[0] for r in self.objects]

    def resolve(self, value, function=None):
        if function and function['address'] <= value < function['address'] + function['size']:
            return 'SELF+' + str(value - function['address'])
        if value in self.names:
            return 'SYMBOL(' + self.names[value] + ')'
        i = bisect_right(self.starts, value) - 1
        if i >= 0:
            start, end, name = self.objects[i]
            if start <= value < end:
                return 'OBJECT(' + name + ')+' + str(value - start)
        return None


TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*.*?\*/|'
                   r'[A-Za-z_][A-Za-z_0-9]*|0[xX][0-9a-fA-F]+|\d+(?:\.\d+)?|[^\s]', re.S)


def pseudocode_features(text, row, addresses):
    # Definition signature is deliberately excluded: interfaces are compared
    # separately by original mangled names. Keep calls, strings and constants.
    text = re.sub(r'(?m)^[^\n;{}]*\([^\n;{}]*\)\s*\n\{', '<SELF_SIGNATURE>\n{', text, count=1)
    renamed = {}
    tokens, shape = [], []
    for match in TOKEN.finditer(text):
        token = match[0]
        if token.startswith(('//', '/*')):
            continue
        if re.fullmatch(r'st_[0-9a-fA-F]+_\d+|v\d+', token):
            if token not in renamed:
                renamed[token] = 'AUTO' + str(len(renamed))
            token = renamed[token]
        numeric = re.fullmatch(r'0[xX][0-9a-fA-F]+|\d+', token)
        if numeric:
            value = int(token, 16 if token.lower().startswith('0x') else 10)
            token = addresses.resolve(value, row) or token
        tokens.append(token)
        shape.append('<NUMBER>' if numeric else token)
    return dict(pseudocode_normalized=sha(' '.join(tokens).encode()),
                pseudocode_shape=sha(' '.join(shape).encode()), token_count=len(tokens)), tokens


def arm_features(code, row, addresses, decoder):
    conservative = []
    for offset in range(0, len(code), 4):
        raw = code[offset:offset+4]
        if len(raw) != 4:
            conservative.append('TAIL:' + raw.hex())
            continue
        word = struct.unpack('<I', raw)[0]
        named = addresses.resolve(word, row)
        if named:
            conservative.append('ADDRESS:' + named)
        elif word & 0x0e000000 == 0x0a000000:
            immediate = word & 0xffffff
            if immediate & 0x800000:
                immediate -= 1 << 24
            target = row['address'] + offset + 8 + immediate * 4
            target_name = addresses.resolve(target, row)
            conservative.append('BRANCH:' + hex(word & 0xff000000) + ':' + (target_name or hex(target)))
        else:
            conservative.append('WORD:' + raw.hex())
    instructions, decoded, shapes = 0, 0, []
    for instruction in decoder.disasm(code, row['address']):
        if not instruction.id:
            shapes.append('DATA:' + instruction.bytes.hex())
            continue
        decoded += instruction.size
        instructions += 1
        operands = instruction.op_str
        if re.fullmatch(r'b(?:l|x|lx)?(?:eq|ne|hs|lo|mi|pl|vs|vc|hi|ls|ge|lt|gt|le|al)?', instruction.mnemonic):
            match = re.fullmatch(r'#(0x[0-9a-fA-F]+|\d+)', operands)
            if match:
                value = int(match[1], 16 if match[1].startswith('0x') else 10)
                operands = addresses.resolve(value, row) or '<EXTERNAL_BRANCH>'
        operands = re.sub(r'#-?(?:0x[0-9a-fA-F]+|\d+)', '#<IMM>', operands)
        shapes.append(instruction.mnemonic + ' ' + operands)
    return dict(address_normalized=sha('\n'.join(conservative).encode()),
                instruction_shape=sha('\n'.join(shapes).encode()),
                decoded_bytes=decoded, instruction_count=instructions,
                linear_decode_fraction=round(decoded / len(code), 6))


def ratio(n, denominator):
    return round(n / denominator, 6) if denominator else None


def compare(left, right):
    names = set(left) & set(right)
    result = dict(client_names=len(left), server_names=len(right), shared_names=len(names),
                  union_names=len(set(left) | set(right)), client_coverage=ratio(len(names), len(left)),
                  server_coverage=ratio(len(names), len(right)), jaccard=ratio(len(names), len(set(left)|set(right))))
    matches = {}
    for field in ('sha256', 'address_normalized', 'instruction_shape', 'pseudocode_normalized', 'pseudocode_shape'):
        eligible = [name for name in names if any(r.get(field) for r in left[name]) and any(r.get(field) for r in right[name])]
        matched = [name for name in eligible if {r.get(field) for r in left[name]} & {r.get(field) for r in right[name]} - {None}]
        matches[field] = dict(comparable_shared_names=len(eligible), matched_names=len(matched),
                              matched_fraction_of_comparable=ratio(len(matched), len(eligible)))
    result['fingerprints'] = matches
    return result


def indexed(rows, predicate=lambda r: True):
    output = defaultdict(list)
    for row in rows:
        if predicate(row):
            output[row['mangled']].append(row)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repository', type=Path)
    args = parser.parse_args()
    assert sys.platform.startswith('linux'), 'Canonical analysis runs on Linux'
    repo = args.repository.resolve()
    lib = repo / 'uc-library'
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    output = lib / 'validation/client-server-similarity' / stamp
    output.mkdir(parents=True, exist_ok=False)
    metadata, all_rows, manifests, provenance = {}, {}, {}, {}
    for role in ('client', 'server'):
        base = lib / 'recovered-all' / role
        manifests[role] = json.loads((base / 'manifest.json').read_text())
        all_rows[role] = json.loads((base / 'all-symbols.json').read_text())
        metadata[role] = [dict(r, role=role, category=category(r), namespace=namespace(r)) for r in all_rows[role] if defined(r)]
        assert len(metadata[role]) == manifests[role]['function_symbols']
        provenance[role] = {name:file_sha(base/name) for name in ('manifest.json','all-symbols.json','trusted-exports.json','deferred-scope.json')}
    common = {r['mangled'] for r in all_rows['client']} & {r['mangled'] for r in all_rows['server']}
    decoder = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM | capstone.CS_MODE_LITTLE_ENDIAN)
    decoder.skipdata = True
    pseudo_sources, body_sources, text_tokens = {}, {}, {}
    for role in ('client', 'server'):
        base = lib / 'recovered-all' / role
        binary = repo / manifests[role]['path']
        assert file_sha(binary) == manifests[role]['sha256']
        raw = binary.read_bytes()
        addresses = AddressNames(all_rows[role], common)
        deferred = {r['address'] for r in json.loads((base/'deferred-scope.json').read_text())['entries']}
        trusted = json.loads((base/'trusted-exports.json').read_text())
        assert trusted['source_sha256'] == manifests[role]['sha256']
        features = {}
        with binary.open('rb') as stream:
            elf = ELFFile(stream)
            for row in metadata[role]:
                if row['address'] in deferred or row['category'] == 'Core source provider':
                    row['core_body_analysis_excluded'] = True
                    continue
                key = (row['address'], row['size'])
                if key not in features:
                    section = elf.get_section(row['section'])
                    assert section['sh_type'] != 'SHT_NOBITS'
                    offset = section['sh_offset'] + row['address'] - section['sh_addr']
                    assert offset == row['file_offset']
                    assert section['sh_addr'] <= row['address'] < row['address']+row['size'] <= section['sh_addr']+section['sh_size']
                    code = raw[offset:offset+row['size']]
                    assert sha(code) == row['sha256'] == file_sha(base/row['export_path'])
                    f = arm_features(code,row,addresses,decoder)
                    path = base/'pseudocode'/f'{row["address"]:08x}.cpp.txt'
                    if path.is_file():
                        digest = file_sha(path)
                        seal = trusted['exports'].get(str(row['address']))
                        assert seal and seal['sha256'] == digest, path
                        text = path.read_text()
                        assert text.startswith('// UNVALIDATED')
                        normalized, tokens = pseudocode_features(text,row,addresses)
                        f.update(normalized)
                        pseudo_sources[str(path.relative_to(lib))] = digest
                        if 'Presonus::DICE::' in row['demangled'] or 'Presonus::NOAA::' in row['demangled']:
                            text_tokens[(role,row['mangled'])] = tokens
                    features[key] = f
                    body_sources[f'{role}:{row["address"]:08x}:{row["size"]}'] = row['sha256']
                row.update(features[key])
        print(json.dumps(dict(role=role, processed_non_core_entries=sum(not r.get('core_body_analysis_excluded') for r in metadata[role]),
                              existing_pseudocode_entries=sum('pseudocode_normalized' in r for r in metadata[role]))),flush=True)
    scopes = {'all_defined_names':lambda r:True,
              'presonus_application':lambda r:r['category']=='Presonus application',
              'non_core':lambda r:r['category']!='Core source provider',
              'core_metadata_only':lambda r:r['category']=='Core source provider'}
    metrics = {name:compare(indexed(metadata['client'],predicate),indexed(metadata['server'],predicate)) for name,predicate in scopes.items()}
    categories = {}
    namespaces = {}
    for name in sorted({r['category'] for rows in metadata.values() for r in rows}):
        categories[name] = compare(indexed(metadata['client'],lambda r:r['category']==name),indexed(metadata['server'],lambda r:r['category']==name))
    for name in sorted({r['namespace'] for rows in metadata.values() for r in rows if r['category']=='Presonus application'}):
        namespaces[name] = compare(indexed(metadata['client'],lambda r:r['namespace']==name),indexed(metadata['server'],lambda r:r['namespace']==name))
    pairs = []
    a,b = map(lambda role:indexed(metadata[role]),('client','server'))
    for name in sorted(set(a)&set(b)):
        x,y = a[name],b[name]
        pairs.append(dict(mangled=name,demangled=x[0]['demangled'],category=x[0]['category'],namespace=x[0]['namespace'],
            client=[{k:r[k] for k in ('address','size','section','file_offset','sha256')} for r in x],
            server=[{k:r[k] for k in ('address','size','section','file_offset','sha256')} for r in y],
            matches={field:bool(({r.get(field) for r in x}&{r.get(field) for r in y})-{None})
                     for field in ('sha256','address_normalized','instruction_shape','pseudocode_normalized','pseudocode_shape')}))
    renamed_pairs = []
    transport = {}
    for role,scope in (('client','DICE'),('server','NOAA')):
        transport[role] = {r['demangled'].replace('Presonus::'+scope+'::','Presonus::<transport>::'):r
                           for r in metadata[role] if r['demangled'].startswith('Presonus::'+scope+'::')}
    for key in sorted(set(transport['client'])&set(transport['server'])):
        x,y = transport['client'][key],transport['server'][key]
        tx,ty = text_tokens.get(('client',x['mangled'])),text_tokens.get(('server',y['mangled']))
        renamed_pairs.append(dict(normalized_signature=key,client=x,server=y,
            pseudocode_token_similarity=SequenceMatcher(None,tx,ty,autojunk=True).ratio() if tx and ty else None,
            known_wait_semantic_difference='NOAA additionally forces its SPI idle pump once at strict >60ms ack / >23ms response, before timeout; DICE has no forced pump.' if 'waitAck(' in key or 'waitResponseSet(' in key else None))
    clusters = {}
    for field in ('address_normalized','pseudocode_normalized','instruction_shape'):
        table = defaultdict(lambda:defaultdict(list))
        for role,rows in metadata.items():
            for r in rows:
                if r['category']=='Presonus application' and r.get(field) and r.get('instruction_count',0)>=8 and r['size']>=32:
                    table[r[field]][role].append(r['mangled'])
        selected=[]
        for digest,roles in table.items():
            if not all(role in roles for role in ('client','server')):continue
            left,right=set(roles['client']),set(roles['server'])
            if left==right and len(left)==1:continue
            selected.append(dict(fingerprint=digest,client_mangles=sorted(left),server_mangles=sorted(right),
                                 different_name_candidate=bool(left-right or right-left)))
        clusters[field]=selected
    aliases = {}
    for role,rows in metadata.items():
        by_address=defaultdict(list)
        for r in rows:by_address[r['address']].append(r['mangled'])
        aliases[role]=dict(function_entries=len(rows),unique_names=len({r['mangled'] for r in rows}),
            unique_addresses=len(by_address),alias_entries_beyond_unique_addresses=len(rows)-len(by_address),
            same_address_symbol_groups={hex(k):v for k,v in by_address.items() if len(v)>1},
            zero_sized_defined_function_rows=sum(r['kind']=='STT_FUNC' and not r['size'] and isinstance(r['section'],int) for r in all_rows[role]),
            imported_function_rows=sum(r['kind']=='STT_FUNC' and not isinstance(r['section'],int) for r in all_rows[role]))
    report=dict(status='analysis only; no reconstruction or readiness promotion',source_elf=manifests,
        tool_sha256=file_sha(Path(__file__)),capstone_version=capstone.__version__,metadata_sha256=provenance,
        metrics=metrics,categories=categories,namespaces=namespaces,aliases=aliases,
        byte_export_ranges_checked=len(body_sources),trusted_non_core_pseudocode_exports_checked=len(pseudo_sources),
        core_body_exclusion={role:dict(namespace_owned_entries=sum(owning_namespace(r['mangled'])=='Core' for r in rows),
             additional_core_keyed_initializer_entries=sum(r['demangled'].startswith(('global constructors keyed to Core::','global destructors keyed to Core::')) for r in rows))
             for role,rows in metadata.items()},
        normalization={
          'address_normalized':'A32 4-byte word sequence. Replace exact named absolute addresses or bounded named STT_OBJECT addresses with symbol+offset; replace B/BL word target with named symbol or SELF+relative offset. Preserve all other bits, immediates, tail bytes. Potential code/data ambiguity and accidental numeric/address collision remain.',
          'instruction_shape':'Linear Capstone A32 decoding with data fallback; retain mnemonic/registers/external named branches and self-relative branch target. Mask all #immediates, including meaningful offsets/IDs. Structural selector ONLY; code/data ambiguity and false positives expected.',
          'pseudocode_normalized':'Existing trusted non-Core export only. Remove comments and one definition signature; alpha-rename generated st_HEX_N and vN identifiers by first occurrence; normalize exact known addresses and bounded object offsets/self addresses. Preserve string tokens, calls and other constants. Similarity does not validate decompiler correctness.',
          'pseudocode_shape':'Same token normalization plus all numeric literals masked. Structural selector ONLY.',
          'renamed_transport':'Pair DICE/NOAA demangled signatures after replacing only their namespace prefix; token similarity uses difflib SequenceMatcher autojunk=True. All namespace/member identities remain recorded separately.'},
        reconstruction_ready=False,original_arm_abi_verified=False,hardware_verified=False,
        recommendation=dict(shared_common_library=True,reason='Large application exact-name overlap, with byte and pattern corroboration quantified separately.',
             implementation='Keep one source tree and one common presonus_uc/presonus_common library. Add presonus_cs18_client and presonus_rm_server role targets linking common code; add executable entry points only when actually recovered. Put transport/hardware/composition differences in narrow role adapters/options. Preserve original namespaces and per-ELF proofs.',
             caution='Same mangles or normalized bodies do not prove equal semantics. Review mismatches and test both role fixtures; use shared helpers with separate original scoped forwarding methods where DICE/NOAA names differ. Never hide real forced-pump/timeout differences.'),
        supporting_existing_candidate='ControlGroup: four common methods/eight ELF entries, actual CCL FixedSizeVector,23,704 total original ARM executions; proof candidates/panel-control-group/validation/validation.json (not promoted by this analysis).')
    write(output/'similarity.json',report)
    write(output/'intersecting-symbols.json',pairs)
    write(output/'renamed-dice-noaa.json',renamed_pairs)
    write(output/'different-name-clusters.json',clusters)
    write(output/'pseudocode-input-hashes.json',pseudo_sources)
    write(output/'verified-byte-ranges.json',body_sources)
    app=metrics['presonus_application']
    lines=['# Client/server common-code similarity','',
        'This compares existing unstripped ELF exports; it does not reconstruct Core, regenerate pseudocode, validate recovered functions, or claim ABI/semantic equivalence.','',
        '| Scope | Client unique names | Server unique names | Shared | Client coverage | Server coverage |',
        '|---|---:|---:|---:|---:|---:|']
    for name,m in metrics.items():
        lines.append(f'| {name} | {m["client_names"]} | {m["server_names"]} | {m["shared_names"]} | {m["client_coverage"]:.2%} | {m["server_coverage"]:.2%} |')
    lines += ['',f'Presonus-owned name instances: {app["client_names"]+app["server_names"]}; union {app["union_names"]}. Reconstructing once per unique original name avoids up to {app["shared_names"]} duplicate role-name tasks ({app["shared_names"]/(app["client_names"]+app["server_names"]):.2%}), before class/alias and behavior review. This is a symbol-work estimate, not a source line estimate.','',
        '## Same-name Presonus comparison','',
        '| Comparison | Comparable shared names | Matches | Fraction |','|---|---:|---:|---:|']
    for name,m in app['fingerprints'].items():
        fraction=f'{m["matched_fraction_of_comparable"]:.2%}' if m['matched_fraction_of_comparable'] is not None else 'n/a'
        lines.append(f'| {name} | {m["comparable_shared_names"]} | {m["matched_names"]} | {fraction} |')
    lines += ['', '## Application scope groups','', 'First nested Presonus scope may be a namespace or a directly nested class; this grouping does not infer original declarations.','', '| First Presonus scope | Client | Server | Shared | Client coverage | Server coverage |','|---|---:|---:|---:|---:|---:|']
    for name,m in sorted(namespaces.items(),key=lambda pair:-pair[1]['shared_names']):
        lc=f'{m["client_coverage"]:.2%}' if m['client_coverage'] is not None else 'n/a'
        rc=f'{m["server_coverage"]:.2%}' if m['server_coverage'] is not None else 'n/a'
        lines.append(f'| {name} | {m["client_names"]} | {m["server_names"]} | {m["shared_names"]} | {lc} | {rc} |')
    lines += ['', '## Interpretation and build recommendation','',report['recommendation']['implementation'],'',report['recommendation']['caution'],'',
        'Core bodies are excluded by the recorded deferred-address policy, owning namespace and explicit Core-keyed global initializer/destructor markers. Core API-name metadata overlap is reported separately; the JSON also separates namespace-owned entries from the additional initializer wrappers. Other C/C++ ownership is intentionally not assumed. Imported and zero-size symbols are excluded from the defined-function denominators; aliases and the duplicated server local DSP name remain explicit in JSON.','',
        'The instruction-shape and numeric-masked decompiler figures are speculative candidates: meaningful field offsets, IDs and timeouts are masked. Conservative address-normalized and constant-preserving text hashes are stronger selectors, but also require dual-role review/behavior fixtures. Linear ARM decoding cannot reliably distinguish every literal pool from instructions.','',
        'DICE/NOAA waits demonstrate why pattern sharing needs explicit policy: both can call one shared helper, while NOAA retains an extra once-only forced SPI pump at its two thresholds. A high similarity ratio must not erase this difference.','',
        'Full identity/mapping data: [intersecting symbols](intersecting-symbols.json), [DICE/NOAA candidates](renamed-dice-noaa.json), [cross-name clusters](different-name-clusters.json), [metrics and normalization rules](similarity.json), [trusted pseudocode input hashes](pseudocode-input-hashes.json).','']
    (output/'REPORT.md').write_text('\n'.join(lines))
    evidence=repo/'evidence/recovery/2026-10-27/client-server-similarity'/stamp
    evidence.mkdir(parents=True,exist_ok=False)
    for path in output.iterdir():shutil.copy2(path,evidence/path.name)
    shutil.copy2(Path(__file__),evidence/'client_server_similarity.py')
    write(evidence/'manifest.json',{p.name:file_sha(p) for p in sorted(evidence.iterdir()) if p.is_file()})
    print(json.dumps(dict(output=str(output.relative_to(repo)),evidence=str(evidence.relative_to(repo)),
                          report_sha256=file_sha(output/'similarity.json'),metrics=metrics),indent=2))


if __name__=='__main__':
    main()
