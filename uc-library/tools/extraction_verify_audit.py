#!/usr/bin/env python3
"""Independent byte/alias/cache audit; never runs or restarts a decompiler."""
import argparse
import collections
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

from elftools.elf.elffile import ELFFile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def process(pid):
    root=Path('/proc')/str(pid)
    if not root.exists():
        return {'pid':pid,'exists':False}
    status={line.split(':',1)[0]:line.split(':',1)[1].strip()
            for line in (root/'status').read_text().splitlines() if ':' in line}
    return {'pid':pid,'exists':True,'state':status.get('State'),
            'rss':status.get('VmRSS'),'virtual':status.get('VmSize'),
            'swap':status.get('VmSwap'),
            'command':[x.decode() for x in (root/'cmdline').read_bytes().split(b'\0') if x]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repository',type=Path)
    args=parser.parse_args()
    library=args.repository/'uc-library'
    target=library/'validation/extraction-verification'
    target.mkdir(parents=True,exist_ok=True)
    result={'snapshot_utc':datetime.now(timezone.utc).isoformat(),'roles':{},
            'pseudocode_semantically_verified':False,'portable_sources_promoted':False}
    for role in ('client','server'):
        root=library/'recovered-all'/role
        manifest=json.loads((root/'manifest.json').read_text())
        binary=args.repository/manifest['path']
        raw=binary.read_bytes()
        assert digest(raw)==manifest['sha256'],'source ELF identity changed'
        symbols=json.loads((root/'symbols.json').read_text())
        functions=[s for s in symbols if s['kind']=='STT_FUNC' and isinstance(s['section'],int) and s['size']]
        by_address=collections.defaultdict(list)
        for sym in functions:by_address[sym['address']].append(sym)
        counts=collections.Counter()
        with binary.open('rb') as stream:
            elf=ELFFile(stream)
            table=elf.get_section_by_name('.symtab')
            expected={(s.name,int(s['st_value']),int(s['st_size']),s['st_shndx'],s['st_info']['type'])
                      for s in table.iter_symbols()}
            for sym in symbols:
                key=(sym['mangled'],sym['address'],sym['size'],sym['section'],sym['kind'])
                assert key in expected,f'original symbol not found: {key}'
                if not isinstance(sym['section'],int) or not sym['size']:continue
                section=elf.get_section(sym['section'])
                address=sym['address']&~1 if sym['kind']=='STT_FUNC' else sym['address']
                assert int(section['sh_addr'])<=address and address+sym['size']<=int(section['sh_addr'])+int(section['sh_size'])
                if section['sh_type']=='SHT_NOBITS':
                    assert 'NOBITS' in sym.get('storage','')
                    counts['nobits']+=1
                    continue
                offset=int(section['sh_offset'])+address-int(section['sh_addr'])
                assert offset==sym['file_offset']
                exported=(root/sym['export_path']).read_bytes()
                assert raw[offset:offset+sym['size']]==exported
                assert digest(exported)==sym['sha256']
                counts['function_bytes' if sym['kind']=='STT_FUNC' else 'data_bytes']+=1
        state_path=root/'decompilation.json'
        entries=json.loads(state_path.read_text()) if state_path.exists() else []
        assert len(entries)==len({e['address'] for e in entries}),'duplicate status addresses'
        assert all(e['address'] in by_address for e in entries),'status outside workload'
        recorded={e['address']:e for e in entries if e['status']=='exported'}
        previous=collections.defaultdict(list)
        for scope in ('recovered','recovered-dice'):
            prior=library/scope/role
            prior_manifest=json.loads((prior/'manifest.json').read_text())
            assert prior_manifest['sha256']==manifest['sha256']
            for entry in json.loads((prior/'decompilation.json').read_text()):
                if entry['status']!='exported':continue
                path=prior/'pseudocode'/f'{entry["address"]:08x}.cpp.txt'
                previous[entry['address']].append((digest(path.read_bytes()),str(path)))
        files=[]
        available=set()
        for path in sorted((root/'pseudocode').glob('*.cpp.txt')):
            address=int(path.name.split('.')[0],16)
            data=path.read_bytes()
            fingerprint=digest(data)
            entry={'address':address,'path':str(path),'bytes':len(data),'sha256':fingerprint}
            if address not in by_address:
                entry['classification']='unexpected_address'
            elif address in recorded:
                assert data.startswith(b'// UNVALIDATED') and len(data)>100,'invalid recorded export'
                entry['classification']='recorded_export'
                available.add(address)
            elif any(value==fingerprint for value,source in previous.get(address,[])):
                entry['classification']='exact_prior_scope_copy'
                entry['prior_scope_sources']=[source for value,source in previous[address] if value==fingerprint]
                available.add(address)
            else:
                entry['classification']='unrecorded_untrusted'
            files.append(entry)
        missing_recorded=[a for a in recorded if not (root/'pseudocode'/f'{a:08x}.cpp.txt').is_file()]
        assert not missing_recorded,'recorded output file missing'
        aliases=[{'address':address,'symbols':[{'mangled':s['mangled'],'size':s['size']} for s in group]}
                 for address,group in by_address.items() if len(group)>1]
        report={'source':str(binary),'source_sha256':manifest['sha256'],
                'function_entries':len(functions),'unique_function_addresses':len(by_address),
                'alias_extra_entries':len(functions)-len(by_address),'aliases':aliases,
                'byte_audit':dict(counts),'recorded_status_counts':dict(collections.Counter(e['status'] for e in entries)),
                'cache_counts':dict(collections.Counter(f['classification'] for f in files)),
                'trusted_available_unique':len(available),'remaining_generation_unique':len(set(by_address)-available),
                'cache_files':files,
                'remaining_functions':[{'address':address,'aliases':[s['mangled'] for s in group]}
                                       for address,group in by_address.items() if address not in available]}
        result['roles'][role]=report
    kernel=subprocess.run(['journalctl','-k','--since','2026-10-26 17:20:00 UTC','--until','2026-10-26 18:05:00 UTC',
                           '--grep','654043|Out of memory|Killed process','--no-pager','-n','20'],
                          text=True,capture_output=True)
    mem={line.split(':',1)[0]:line.split(':',1)[1].strip() for line in Path('/proc/meminfo').read_text().splitlines()}
    result['resources']={'client_process':process(654042),'server_process':process(654043),
                         'memory':{key:mem.get(key) for key in ('MemTotal','MemAvailable','SwapTotal','SwapFree')},
                         'server_terminal_exit_code_from_checkpoint':137,
                         'kernel_query_returncode':kernel.returncode,'kernel_evidence':kernel.stdout,
                         'server_oom_confirmed':kernel.returncode==0 and 'Killed process 654043' in kernel.stdout and 'oom' in kernel.stdout.lower()}
    (target/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
    summary={'snapshot_utc':result['snapshot_utc'],'roles':{},'resources':result['resources']}
    for role,report in result['roles'].items():
        summary['roles'][role]={key:report[key] for key in ('function_entries','unique_function_addresses','alias_extra_entries','byte_audit','recorded_status_counts','cache_counts','trusted_available_unique','remaining_generation_unique')}
    (target/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':main()
