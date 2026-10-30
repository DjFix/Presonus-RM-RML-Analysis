#!/usr/bin/env python3
"""Generate Markdown coverage tables without equating decompilation with verification."""
import argparse
import collections
import hashlib
import html
import json
import re
from pathlib import Path
from extraction_verify_bounded import owning_namespace
from merge_readiness import proof_covers, repository_sources_match
from source_provider_tracking import load_source_providers


BEHAVIOR = {
    'Presonus::UC::EventClass::write(Presonus::UC::BufferWriter&, Presonus::UC::Event const&) const': 'event-header layout',
    'Presonus::UC::Connection::writeEvent(Presonus::UC::Connection::ChannelWriter&, Presonus::UC::Event const&)': 'TCP framing only',
    'Presonus::UC::Connection::readEvents()': 'TCP framing only',
    'Presonus::UC::MulticastConnection::writeEvent(Core::Sockets::CoreSocket*, Core::Sockets::IPAddress const&, Presonus::UC::Event const&)': 'UDP framing only',
    'Presonus::UC::ParamValueEventClass::write(Presonus::UC::BufferWriter&, Presonus::UC::ParamValueEvent const&) const': 'PV payload only',
    'Presonus::UC::ParamValueEventClass::read(Presonus::UC::ParamValueEvent&, Presonus::UC::BufferReader&) const': 'PV payload only',
}


def code(text):
    return '<code>'+html.escape(str(text)).replace('|','&#124;')+'</code>'


def group(name):
    # Avoid substring errors such as cateGORy or perioDICEvent being called DICE.
    if re.search(r'Presonus::DICE::|::Dice[A-Z0-9]|::initDice|::Shelby|^dice[0-9_]|^tcat_|^shelby',name):
        return 'DICE / TCAT / Shelby'
    for namespace,label in [('UC','UC'),('Surface','Surface'),('Mixer','Mixer'),('Panel','Panel'),
                            ('Dsp','DSP'),('AVB','AVB'),('NOAA','NOAA'),('XMen','XMen'),('UUX','UUX')]:
        if f'Presonus::{namespace}::' in name:
            return label
    if 'panel_surface_code' in name:
        return 'Panel'
    if 'Core::' in name:
        return 'Core'
    if 'Presonus::' in name:
        return 'Other Presonus'
    if 'std::' in name or name.startswith(('__','_Unwind','operator ')):
        return 'C++ / compiler runtime'
    return 'Other C / application'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library',type=Path,default=Path(__file__).resolve().parents[1])
    locations=parser.add_mutually_exclusive_group(required=True)
    locations.add_argument('--inputs',type=Path)
    locations.add_argument('--repository',type=Path)
    args=parser.parse_args()
    library=args.library.resolve()
    target=library/'tracking'
    target.mkdir(exist_ok=True)
    work_scope_path=target/'work-scope.json'
    work_scope=json.loads(work_scope_path.read_text()) if work_scope_path.exists() else {}
    deferred_namespaces=set(work_scope.get('deferred_original_namespaces',[]))
    source_providers,source_provenance=load_source_providers(library,work_scope.get('source_policy',{}))
    integration_file=library/'validation/integration.json'
    integrated=json.loads(integration_file.read_text()) if integration_file.exists() else {}
    integrated_log=next((parent/integrated['test_log'] for parent in (library,*library.parents)
                         if integrated.get('test_log') and (parent/integrated['test_log']).is_file()),None)
    tests_passed=bool(integrated.get('ctest_passed')) and bool(integrated.get('files')) and \
        all((library/name).is_file() and hashlib.sha256((library/name).read_bytes()).hexdigest()==digest
            for name,digest in integrated.get('files',{}).items()) and \
        integrated_log is not None and hashlib.sha256(integrated_log.read_bytes()).hexdigest()==integrated.get('test_log_sha256')
    ready={}
    format_path=library/'validation/formatting.json'
    current_format=json.loads(format_path.read_text()) if format_path.exists() else {}
    config=next((parent/'.clang-format' for parent in (library,*library.parents) if (parent/'.clang-format').is_file()),None)
    format_valid=bool(current_format.get('format_check_passed')) and config is not None and hashlib.sha256(config.read_bytes()).hexdigest()==current_format.get('configuration_sha256')
    ready_ledger=library/'validation/ready-functions.json'
    if ready_ledger.exists():
        for item in json.loads(ready_ledger.read_text()).get('functions',[]):
            if not repository_sources_match(library,item):
                continue
            validation=library/item['validation']
            if not validation.is_file() or hashlib.sha256(validation.read_bytes()).hexdigest()!=item['validation_sha256']:
                continue
            proof=json.loads(validation.read_text())
            if not proof_covers(proof,item):
                continue
            if not all((library/path).is_file() and hashlib.sha256((library/path).read_bytes()).hexdigest()==digest for path,digest in item['sources'].items()):
                continue
            if not format_valid or not all(current_format.get('files',{}).get(path)==digest for path,digest in item['sources'].items() if Path(path).suffix in ('.cpp','.hpp','.h')):
                continue
            ready[(item['original_elf_sha256'],item['mangled'])]=item
    compiled_pending={}
    pending_ledger=library/'validation/compiled-functions.json'
    if pending_ledger.exists():
        for item in json.loads(pending_ledger.read_text()).get('functions',[]):
            if not repository_sources_match(library,item):
                continue
            path=library/item['validation']
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=item['validation_sha256']:continue
            if not all((library/name).is_file() and hashlib.sha256((library/name).read_bytes()).hexdigest()==digest for name,digest in item['sources'].items()):continue
            proofs=json.loads(path.read_text())
            if isinstance(proofs,dict):proofs=proofs.get('functions',[proofs])
            if not any(p.get('mangled')==item['mangled'] and p.get('original_elf_sha256')==item['original_elf_sha256'] and p.get('cpp_compiled') and p.get('mangling_namespace_checked') for p in proofs):continue
            compiled_pending[(item['original_elf_sha256'],item['mangled'])]=item
    result={'verification_policy':{'byte_verification':'Original ELF identity, byte slice and exported-byte hash checked; not semantic verification.',
                                   'pseudocode':'Exported only; not compiled or behaviorally verified.',
                                   'complete_original_function_verification':False,
                                   'hardware_testing':'Deferred by user; hardware unavailable.'},
            'portable_ctest_evidence_available':tests_passed,'work_scope':work_scope,
            'upstream_source_provenance':source_provenance,'roles':{}}
    main_rows=[]
    subsystem_rows=[]
    for role,label,filename in [('client','CS18AI surface 13840','surface-13840.elf'),('server','RM/RML mixer 13731','mixer-13731.elf')]:
        root=library/'recovered'/role
        manifest=json.loads((root/'manifest.json').read_text())
        source=((args.inputs/filename) if args.inputs else args.repository/manifest['path']).resolve()
        raw=source.read_bytes()
        assert hashlib.sha256(raw).hexdigest()==manifest['sha256'], f'{role}: original ELF identity mismatch'
        symbols=json.loads((root/'all-symbols.json').read_text())
        deferred_addresses={sym['address'] for sym in symbols
                            if sym['kind']=='STT_FUNC' and isinstance(sym['section'],int) and sym['size']
                            and owning_namespace(sym['mangled']) in deferred_namespaces}
        selected=collections.defaultdict(list)
        trusted_indexes={}
        scopes=[]
        for directory in ('recovered','recovered-dice','recovered-all'):
            scoped_root=library/directory/role
            if not (scoped_root/'manifest.json').exists():
                continue
            scoped_manifest=json.loads((scoped_root/'manifest.json').read_text())
            assert scoped_manifest['sha256']==manifest['sha256'], 'scope uses a different ELF'
            index_path=scoped_root/'trusted-exports.json'
            if index_path.exists():
                index=json.loads(index_path.read_text())
                assert index['source_sha256']==manifest['sha256'], 'pseudocode index uses a different ELF'
                trusted_indexes[scoped_root]=index['exports']
            status_file=scoped_root/'decompilation.json'
            statuses={s['address']:s for s in json.loads(status_file.read_text())} if status_file.exists() else {}
            scopes.append(dict(directory=directory,manifest=scoped_manifest))
            for item in json.loads((scoped_root/'symbols.json').read_text()):
                selected[(item['mangled'],item['address'],item['size'],item['section'])].append((item,scoped_root,statuses))
        entries=[]
        for sym in symbols:
            if sym['kind'] not in ('STT_FUNC','STT_OBJECT'):
                continue
            entry=dict(sym)
            entry.update(subsystem=group(sym['demangled']),defined=isinstance(sym['section'],int),
                         bytes_extracted=False,bytes_verified=False,pseudocode_exported=False,
                         original_function_verified=False,portable_behavior='not verified',
                         cpp_compiled=False,mangled_name_verified=False,portable_ready=False)
            entry['work_deferred']=sym['kind']=='STT_FUNC' and (
                owning_namespace(sym['mangled']) in deferred_namespaces or
                (entry['defined'] and bool(sym['size']) and sym['address'] in deferred_addresses))
            entry['work_scope']=('manual recovery deferred: Core; upstream mapping pending' if work_scope.get('source_policy',{}).get('requested') else 'deferred by user: Core owner/alias') if entry['work_deferred'] else ('eligible' if sym['kind']=='STT_FUNC' else 'data catalogue')
            provider=source_providers.get((manifest['sha256'],sym['mangled'],sym['address'],sym['size']))
            entry['upstream_api_match']=provider is not None
            entry['upstream_body_available']=bool(provider and provider['source_body_available'])
            if provider:
                entry.update(work_scope='upstream API preferred; manual recovery skipped',
                             upstream_commit=provider['upstream_commit'],
                             upstream_source=provider['upstream'][0]['url'],
                             source_provider_status=provider['status'])
            candidates=selected.get((sym['mangled'],sym['address'],sym['size'],sym['section']),[])
            for recovered,scoped_root,statuses in candidates:
                if 'storage' in recovered:
                    entry['storage']=recovered['storage']
                relative=recovered.get('export_path')
                if relative is None and sym['kind']=='STT_FUNC' and 'file_offset' in recovered:
                    relative=f'machine-code/{sym["address"]&~1:08x}.bin'
                exported=scoped_root/relative if relative else None
                if exported is not None and exported.is_file():
                    data=exported.read_bytes()
                    offset=recovered['file_offset']
                    assert data==raw[offset:offset+sym['size']], f'{role}: exported bytes differ for {sym["mangled"]}'
                    assert hashlib.sha256(data).hexdigest()==recovered['sha256'], 'export hash mismatch'
                    entry.update(bytes_extracted=True,bytes_verified=True,
                                 machine_code='../'+str(exported.relative_to(library)))
                status=statuses.get(sym['address'])
                pseudo=scoped_root/'pseudocode'/f'{sym["address"]:08x}.cpp.txt'
                if sym['kind']=='STT_FUNC' and status and status['status']=='exported' and pseudo.is_file():
                    assert pseudo.read_text().startswith('// UNVALIDATED'), 'pseudocode warning missing'
                    if scoped_root in trusted_indexes:
                        sealed=trusted_indexes[scoped_root].get(str(sym['address']))
                        assert sealed is not None, 'exported pseudocode lacks its trusted index record'
                        assert hashlib.sha256(pseudo.read_bytes()).hexdigest()==sealed['sha256'], 'pseudocode hash mismatch'
                    entry.update(pseudocode_exported=True,pseudocode='../'+str(pseudo.relative_to(library)),
                                 pseudocode_aliases=status.get('aliases',[status['mangled']]))
                if sym['kind']=='STT_FUNC' and tests_passed and sym['demangled'] in BEHAVIOR:
                    entry['portable_behavior']='partial: '+BEHAVIOR[sym['demangled']]
            implementation=ready.get((manifest['sha256'],sym['mangled']))
            pending=compiled_pending.get((manifest['sha256'],sym['mangled']))
            if pending is not None and sym['kind']=='STT_FUNC':
                entry.update(cpp_compiled=True,mangled_name_verified=True,
                    validation='../'+pending['validation'],declaration_pending=pending.get('unresolved','Original declaration unresolved'),
                    portable_behavior='ARM state/value fixtures passed; original declaration pending')
            if implementation is not None and sym['kind']=='STT_FUNC':
                entry.update(cpp_compiled=True,mangled_name_verified=True,portable_ready=True,
                    validation='../'+implementation['validation'],validation_domain=implementation['domain'],
                    portable_behavior='ARM differential passed; recorded validation domain')
            entries.append(entry)
        functions=[e for e in entries if e['kind']=='STT_FUNC']
        data_symbols=[e for e in entries if e['kind']=='STT_OBJECT']
        defined=[e for e in functions if e['defined'] and e['size']]
        summary=dict(label=label,source=str(source),sha256=manifest['sha256'],
                     total_named_symbols=len(symbols),function_symbol_entries=len(functions),
                     defined_nonempty_function_entries=len(defined),data_symbol_entries=len(data_symbols),
                     byte_verified_functions=sum(e['bytes_verified'] for e in functions),
                     byte_verified_data_symbols=sum(e['bytes_verified'] for e in data_symbols),
                     pseudocode_exports=sum(e['pseudocode_exported'] for e in defined),
                     pseudocode_unique_entry_addresses=len({e['address'] for e in defined if e['pseudocode_exported']}),
                     pseudocode_zero_size_alias_exports=sum(e['defined'] and not e['size'] and e['pseudocode_exported'] for e in functions),
                     fully_verified_original_functions=0,
                     portable_partial_behavior_references=sum(e['portable_behavior']!='not verified' for e in functions))
        summary['portable_reconstructions_ready']=sum(e['portable_ready'] for e in functions)
        summary['compiled_declaration_pending_ranges']=sum(e['cpp_compiled'] and not e['portable_ready'] for e in functions)
        summary['compiled_declaration_pending_entries']=len({e['mangled'] for e in functions if e['cpp_compiled'] and not e['portable_ready']})
        summary['deferred_function_entries']=sum(e['work_deferred'] for e in defined)
        summary['eligible_function_entries']=len(defined)-summary['deferred_function_entries']
        summary['upstream_source_api_matches']=sum(e['upstream_api_match'] for e in defined)
        summary['upstream_source_bodies_available']=sum(e['upstream_body_available'] for e in defined)
        summary['upstream_declaration_only_matches']=summary['upstream_source_api_matches']-summary['upstream_source_bodies_available']
        result['roles'][role]=dict(summary=summary,scopes=scopes,symbols=entries)
        main_rows.append(f'| {label} | {len(defined):,} | {summary["byte_verified_functions"]:,} | {summary["pseudocode_exports"]:,} | {summary["upstream_source_api_matches"]:,} ({summary["upstream_source_bodies_available"]:,} bodies) | {summary["portable_reconstructions_ready"]} | {summary["compiled_declaration_pending_entries"]} | 0 | [functions](tracking/{role}-functions.md), [data](tracking/{role}-data.md) |\n')
        for subsystem in sorted({e['subsystem'] for e in defined}):
            subset=[e for e in defined if e['subsystem']==subsystem]
            subsystem_rows.append(f'| {role} | {subsystem} | {len(subset):,} | {sum(e["bytes_verified"] for e in subset):,} | {sum(e["pseudocode_exported"] for e in subset):,} |\n')
        for category,rows in [('functions',functions),('data',data_symbols)]:
            lines=[f'# {label}: {category}\n\n',
                   '[Coverage index](../SYMBOLS.md). Generated from `all-symbols.json`; do not edit status cells manually.\n\n',
                   f'Input ELF SHA-256: `{manifest["sha256"]}`.\n\n',
                   '**Verified bytes** means an exact match to the original ELF, not a verified implementation. ',
                   '**Exported** pseudocode is unvalidated. Every original function remains semantically unverified. ',
                   'Partial portable behavior labels refer only to the narrower tests listed in the coverage index.\n\n']
            for subsystem in sorted({e['subsystem'] for e in rows}):
                lines.extend([f'## {subsystem}\n\n',
                              '| Address | Size | C++ signature / symbol | Mangled name | Work scope | Bytes | Pseudocode | C++ / mangling | Portable behavior |\n',
                              '|---|---:|---|---|---|---|---|---|---|\n'])
                for entry in sorted((e for e in rows if e['subsystem']==subsystem),key=lambda e:(e['address'],e['mangled'])):
                    if not entry['defined']:
                        byte_status='import; no body in ELF'
                    elif not entry['size']:
                        byte_status='zero-size symbol'
                    elif entry['bytes_verified']:
                        byte_status=f'[verified]({entry["machine_code"]})'
                    elif 'storage' in entry:
                        byte_status=entry['storage']
                    else:
                        byte_status='not extracted'
                    pseudo=f'[exported; unvalidated]({entry["pseudocode"]})' if entry['pseudocode_exported'] else 'not exported'
                    behavior=entry['portable_behavior'] if category=='functions' else 'not verified'
                    compiled=f'[ready; names matched]({entry["validation"]})' if entry['portable_ready'] else ('not reconstructed' if category=='functions' else 'N/A')
                    if entry['cpp_compiled'] and not entry['portable_ready']:
                        compiled=f'[compiled; declaration pending]({entry["validation"]})'
                    if entry['upstream_api_match'] and not entry['cpp_compiled']:
                        source_label='upstream body available; native linkage unchecked' if entry['upstream_body_available'] else 'upstream declaration match; body pending'
                        compiled=f'[{source_label}]({entry["upstream_source"]})'
                    lines.append(f'| `0x{entry["address"]:08x}` | {entry["size"]} | {code(entry["demangled"])} | {code(entry["mangled"])} | {entry["work_scope"]} | {byte_status} | {pseudo} | {compiled} | {behavior} |\n')
                lines.append('\n')
            (target/f'{role}-{category}.md').write_text(''.join(lines))
    (target/'coverage.json').write_text(json.dumps(result,indent=2)+'\n')
    header='''# Firmware symbol extraction and verification tracker

The extraction order is **DICE first, then the other mixer/surface functions**.
Tables are regenerated from completed byte exports and recorded per-address
decompiler results across UC, DICE and full-binary recovery scopes.
Unprocessed entries remain marked pending; exported pseudocode is not ready C++.

## Status meanings

- **Catalogued:** name, address, size and section appear in the original symbol table.
- **Bytes verified:** exported function bytes match the SHA-256-identified source ELF and their recorded hash. This does not verify behavior or recover source code.
- **Pseudocode exported:** decompiler produced text. It is unvalidated and excluded from the C++ build.
- **Upstream API match:** the pinned source's compiler-mangled encoded interface matches the original ELF entry. Actual source/body hashes are checked; unencoded original return types, layouts, binary behavior and native build success are not implied. Declaration-only matches are counted separately in coverage JSON.
- **Portable behavior partial:** a narrower wire behavior has a reconstructed C++ implementation and captured-frame tests. This does not verify the entire original function, its ABI or error paths.
- **Portable reconstruction ready:** current formatted C++ sources compiled, original mangled names matched, and ARM differential checks passed within the linked proof's stated domain. Original layouts, unresolved declaration spelling, untested inputs and hardware remain subject to the proof's limitations.
- **Compiled; declaration pending:** C++ compilation and symbol checks passed, but unresolved original interface declarations prevent portable readiness. Summary entries count distinct `(ELF SHA-256, mangled name)` identities; `compiled_declaration_pending_ranges` counts all matching original table rows. Every original range remains a separate table row and requires its own evidence.
- **Original function fully verified:** requires an explicit semantic/differential validation record. There are currently **zero** such functions.
- **Hardware verified:** deferred by the user because CS18AI/RM hardware is unavailable. Nothing is hardware-verified.

Function tables include defined functions and imported function symbols; the counts below refer only to defined, nonempty function entries. Addresses identify the original ARM ELF, not portable-library entry points.
Pseudocode coverage counts defined nonempty symbol entries, including aliases sharing an exported entry point. Unique entry counts and zero-size alias exports are recorded separately in coverage JSON; every symbol's byte range remains independently checked.
Data tables cover `STT_OBJECT` symbols, including embedded firmware and vtables. Structural mapping/file/section symbols remain in `recovered/*/all-symbols.json` and are excluded from the extraction workload.

## Coverage

| Binary | Defined functions | Bytes verified | Pseudocode exported | Upstream API matches (bodies) | Portable reconstructions ready | Compiled; declaration pending | Original functions fully verified | Tables |
|---|---:|---:|---:|---:|---:|---:|---:|---|
'''
    footer='''
## Partial portable C++ evidence

The six labeled original function signatures in each binary have **partial behavior references**, not full semantic verification:

| Original function area | Narrower reconstructed behavior | Evidence |
|---|---|---|
| `EventClass::write` | Event tag and route-field wire layout | `src/protocol.cpp`; captured event roundtrips |
| `Connection::writeEvent`, `Connection::readEvents` | TCP envelope, size bounds, incremental framing | `src/protocol.cpp`; 380 distinct captured TCP frames and malformed/split/coalesced cases |
| `MulticastConnection::writeEvent` | UDP envelope and reply-port field | `src/protocol.cpp`; 14,258 distinct captured UDP frames |
| `ParamValueEventClass::write`, `read` | Parameter-value path/index/value payload | `src/protocol.cpp`; 213 distinct captured PV payloads |

Tests also cover a portable TCP client/server loopback exchange. They do not validate mixer state, subscriptions, authentication, DICE hardware I/O, firmware programming, audio routing or original function equivalence.

Integrated CTest evidence must match current source and log hashes before partial wire-behavior labels are shown. Existing UC byte-export audit: [audit.json](recovered/audit.json). Current source identity, scope manifests, aliases and per-symbol statuses: [coverage.json](tracking/coverage.json).

Current integrated build evidence and source hashes are in [integration.json](validation/integration.json), with the matching [Linux build seal](validation/integration-linux.json). Embedded DICE callbacks have a separate [symbol tracker](validation/dice-image/EMBEDDED-SYMBOLS.md) and [image report](validation/dice-image/REPORT.md); registration labels and independent wrappers do not count as recovered host ELF symbols. [Source-lineage research](validation/source-lineage/README.md) records candidate declarations and version/licensing limitations without promoting them to original headers.

## Subsystem queue

Grouping below is based on symbol names and is a navigation aid, not a proven module/dependency boundary. DICE includes explicit `Presonus::DICE`, `Dice*`, TCAT and Shelby names. Embedded processor firmware and FPGA blobs are data, not automatically disassembled host functions.

| Binary role | Subsystem | Defined functions | Bytes verified | Pseudocode exported |
|---|---|---:|---:|---:|
'''
    trailer='''
## Updating the tracker

Regenerate with `tools/generate_symbol_tracking.py --inputs <directory-containing-surface-13840.elf-and-mixer-13731.elf>` after each extraction phase. This checks source identities and each existing byte export again. Keep semantic/hardware verification false until concrete validation evidence is added; do not promote pseudocode exports to verified source.

The generator merges `recovered`, `recovered-dice` and `recovered-all`, verifies source identity and available byte exports, and uses recorded decompilation results. Function aliases sharing an entry address share a pseudocode export; every symbol's own byte range is checked separately. `validation/ready-functions.json` grants portable readiness only when its proof file and current source hashes match, compiled mangled names were checked, and ARM differential tests passed. Readiness applies only to the recorded buffer/semantic domain; it does not establish original ARM object-layout or hardware compatibility. No original implementation is promoted to fully verified merely because a portable reconstruction is ready.
'''
    scope_path=target/'work-scope.json'
    if scope_path.exists():
        scope=json.loads(scope_path.read_text())
        if 'Core' in scope.get('deferred_original_namespaces',[]):
            source_notice=('Upstream Core source integration and prototype/mangling matching are active, using the earliest verified official public version. Source availability will be tracked separately from binary-behavior validation. ' if scope.get('source_policy',{}).get('requested') else '')
            header=header.replace('## Coverage\n',
                '## Current work scope\n\n'
                'New **manual Core-owned binary reconstruction and extraction are deferred** and remain incomplete. '
                +source_notice+
                'Existing evidence is preserved. Presonus UC/DICE and mixer/surface work continues; '
                'a Core parameter type does not defer a Presonus-owned method. '
                'See [work-scope.json](tracking/work-scope.json).\n\n## Coverage\n')
    provider_report=library/'validation/core-upstream/root-provider-validation.json'
    if provider_report.is_file():
        provider=json.loads(provider_report.read_text())
        if provider.get('passed') and provider.get('relocated_package_consumer_passed'):
            footer += ('\nActual pinned CCL source is built and publicly linked on Linux. '
                       'Its relocated installed package passed a consumer check; all 248 SDK headers matched '
                       'the clean upstream source. This does not promote Core ELF symbols to recovered readiness. '
                       'See [source-provider proof](validation/core-upstream/root-provider-validation.json).\n\n')
    if (library/'validation/RECOVERY-GAPS.md').is_file():
        trailer += ('\nStopped or unsupported reconstruction attempts are recorded in '
                    '[the recovery gap log](validation/RECOVERY-GAPS.md), with exact original identities '
                    'and remaining work. A tool stop does not prove a function unrecoverable.\n')
    if (library/'cmake/CommonObjects.cmake').is_file():
        trailer += ('\nClient/server component targets `presonus::cs18_components` and '
                    '`presonus::rm_components` share production OBJECT units; '
                    '`presonus::uc` remains the compatibility archive. See '
                    '[source partitions](cmake/ProductionSourceGroups.cmake) and '
                    '[production audit](candidates/common-build/validation/production-audit-01/validation.json). '
                    'These component archives do not establish completed application startup.\n')
    (library/'SYMBOLS.md').write_text(header+''.join(main_rows)+footer+''.join(subsystem_rows)+trailer)
    print(json.dumps({role:value['summary'] for role,value in result['roles'].items()},indent=2))


if __name__=='__main__':
    main()
