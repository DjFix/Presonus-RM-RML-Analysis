#!/usr/bin/env python3
"""Seal pinned-source API matches without granting binary-behavior readiness."""
import argparse
import collections
import hashlib
import html
import json
from pathlib import Path
from core_upstream_match import atomic, family, sha
from core_upstream_probe import callable_parts


def code(value):return '<code>'+html.escape(str(value)).replace('|','&#124;')+'</code>'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--analysis',type=Path,required=True)
    parser.add_argument('--probes',type=Path,required=True)
    parser.add_argument('--library',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    analysis=args.analysis.resolve();probes=args.probes.resolve();library=args.library.resolve();out=args.output.resolve()
    out.mkdir(parents=True,exist_ok=True)
    configuration=json.loads((analysis/'configuration.json').read_text());commit=configuration['commit'];source=Path(configuration['source'])
    definitions=json.loads((analysis/'declarations.json').read_text())
    by_family=collections.defaultdict(list)
    for value in definitions:by_family[family(value['name'])].append(value)
    generated=json.loads((probes/'generated-mangles.json').read_text())
    probe_records={item['mangled']:item for item in json.loads((probes/'probes.json').read_text())}
    roles={};skip=[];summaries=[]
    for role in ('client','server'):
        original=json.loads((analysis/(role+'-functions.json')).read_text());records=[]
        for item in original['functions']:
            item=dict(item)
            direct=bool(item['exact_encoded_interface_match'])
            matches=generated.get(item['mangled'],[])
            if not direct and matches:
                item.update(exact_encoded_interface_match=True,upstream=matches,source_body_available=any(match.get('generic_definitions') for match in matches),
                    matching_method='compiler callable probe / actual CXX mangling variants',skip_manual_reconstruction=True,
                    status='upstream-source-provided; binary behavior unverified')
            elif direct:item['matching_method']='compiler-mangled source declaration and definition'
            item['compiled_source_match']=False  # AST mangling != emitted object/link test.
            item['original_function_verified']=False;item['hardware_verified']=False
            for match in item.get('upstream',[]):
                match['source_sha256']=sha(source/match['path'])
                match['url']=f'https://github.com/cclsoftware/ccl-framework/blob/{commit}/{match["path"]}#L{match["line"]}'
            if not item['exact_encoded_interface_match']:
                probe=probe_records.get(item['mangled'])
                if probe and probe.get('status')=='call compatible but different mangling':
                    item['upstream_call_compatible_replacements']=probe.get('referenced',[])
                    item['status']='upstream source preferred; API adaptation required'
                    item['category']='call compatible source API with different mangling'
                try:name,owner,method,arguments,suffix=callable_parts(item['demangled'])
                except ValueError:name=''
                candidates=by_family.get(family(name),[]) if name else []
                if candidates:
                    item['upstream_callable_family_candidates']=candidates
                    item['upstream_template_family_available']='<' in item['demangled']
            if item['exact_encoded_interface_match']:
                skip.append(dict(role=role,mangled=item['mangled'],original_elf_sha256=item['original_elf_sha256'],
                    original_address=item['address'],original_size=item['size'],upstream_commit=commit,
                    status='provided-by-upstream-source; original behavior/ABI unverified',skip_manual_reconstruction=True,
                    matching_method=item['matching_method'],upstream=item['upstream'],
                    source_body_available=item.get('source_body_available',False),
                    original_return_type_recovered=False,original_function_verified=False,hardware_verified=False))
            records.append(item)
        summary=dict(total=len(records),direct_matches=sum(item['matching_method']=='compiler-mangled source declaration and definition' for item in records if 'matching_method' in item),
            exact_encoded_interface_matches=sum(item['exact_encoded_interface_match'] for item in records),
            source_body_available=sum(item.get('source_body_available',False) for item in records if item['exact_encoded_interface_match']),
            source_api_adaptation_candidates=sum('upstream_call_compatible_replacements' in item for item in records),
            remaining_categories=dict(collections.Counter(item.get('category','unclassified') for item in records if not item['exact_encoded_interface_match'])))
        roles[role]=summary
        atomic(out/(role+'-functions.json'),dict(role=role,original_elf_sha256=original['original_elf_sha256'],commit=commit,summary=summary,functions=records))
        lines=[f'# {role}: Core source API mapping\n\n',f'Pinned upstream: `{commit}`. Original ELF SHA-256: `{original["original_elf_sha256"]}`.\n\n',
            'An exact match is a compiler-mangled encoded-interface match. Ordinary return declarations, object layouts, calling behavior and ARM ABI are not recovered by that match. Upstream methods are source-provided under the user-selected source-port policy, not original-behavior-verified.\n\n',
            '| Address | Size | Original signature | Original mangled name | Source-port state | Upstream source |\n|---|---:|---|---|---|---|\n']
        for item in sorted(records,key=lambda value:(value['address'],value['mangled'])):
            links=[]
            for match in item.get('upstream',[])[:3]:links.append(f'[{match["path"]}:{match["line"]}]({match["url"]})')
            lines.append(f'| `0x{item["address"]:08x}` | {item["size"]} | {code(item["demangled"])} | {code(item["mangled"])} | {item["status"]} | '+', '.join(links)+' |\n')
        (out/(role+'-functions.md')).write_text(''.join(lines))
    artifacts=[analysis/'configuration.json',analysis/'source-files.json',analysis/'parse-units.json',analysis/'declarations.json',analysis/'classes.json',probes/'probes.json',probes/'generated-mangles.json',probes/'umbrella.json']
    summary=dict(commit=commit,roles=roles,source_policy='Prefer earliest official source; skip manual recovery for exact encoded-interface matches; adapt app-specific uses of divergent APIs.',
        parser_target='armv5te-unknown-linux-gnueabi',cpp_standard='c++17',
        original_arm_abi_verified=False,binary_behavior_verified=False,hardware_verified=False,
        inputs={str(path.relative_to(library)):sha(path) for path in artifacts})
    atomic(out/'summary.json',summary)
    atomic(out/'manual-recovery-exclusions.fragment.json',dict(upstream_commit=commit,functions=skip,original_function_verified=False,hardware_verified=False))
    readme=['# Earliest official Core source integration\n\n',f'Baseline: **CCL 5.0.0**, Git root/tag `{commit}`, 2026-01-12. The selected source is not claimed to be the firmware-era release.\n\n',
        'Official upstream is registered as `third_party/ccl-framework` (Core under `core/`), pinned by Git submodule gitlink. Upstream namespaces and license notices are unchanged.\n\n',
        '| ELF | Original Core names | Direct source matches | Total exact encoded-interface matches | Source definitions available | Call-compatible API changes |\n|---|---:|---:|---:|---:|---:|\n']
    for role,summary in roles.items():readme.append(f'| {role} | {summary["total"]} | {summary["direct_matches"]} | {summary["exact_encoded_interface_matches"]} | {summary["source_body_available"]} | {summary["source_api_adaptation_candidates"]} |\n')
    readme += ['\nThe complete per-original-symbol JSON and Markdown tables retain original mangled identity, ELF hash, address, size and source links. `manual-recovery-exclusions.fragment.json` is an upstream-provider skip list, **not** a differential-readiness fragment.\n\n',
        '## Verification boundaries\n\n',
        '- Every selected Core file matched its Git blob ID. Original ELF hashes and every Core symbol/address/size/section tuple were re-read from `.symtab`.\n',
        '- API analysis uses actual Linux ARM glibc/libstdc++ sysroot headers. Real Ubuntu PNG/Zlib/DNS-SD development headers supply external declarations. No Core or application class definitions were fabricated. Only build timestamp/revision metadata was generated explicitly for analysis.\n',
        '- Source definitions were parsed with function bodies; callable probes use unevaluated calls and disabled access checks. Constructor/destructor variants come from libclang CXX mangling APIs. Unresolved templates, local functions and thunks remain separately visible.\n',
        '- Ordinary ELF mangling does not reveal original non-template return spelling, complete class layout or semantic equivalence. Source availability and a mangled API match do not establish emitted object/link success, original behavior, hardware behavior or ARM ABI.\n',
        '- Upstream source is preferred for differing APIs. Call-compatible replacements and source-family candidates are migration evidence, not exact matches. Remaining app-specific types and call-site adaptations require separate recovery.\n',
        '- Imported Core files are upstream code and must not be reformatted or manually duplicated as reconstructed implementations.\n']
    (out/'README.md').write_text(''.join(readme))
    print(json.dumps(dict(commit=commit,roles=roles,skip_entries=len(skip)),indent=2))


if __name__=='__main__':main()
