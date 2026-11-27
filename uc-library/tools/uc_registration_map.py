#!/usr/bin/env python3
"""Map original constructor registration coverage without reconstructing Core."""
import argparse,hashlib,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'registry'))
from adapter import snapshot, catalog_roles

def registration_inputs(library, db=None):
 with snapshot(library,db) as registry:
  roles=catalog_roles(registry.c)
  ready={(s['mangled'],s['original_elf_sha256']) for s in registry.ready['functions']}
  provenance=registry.provenance()
 return roles,ready,provenance

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('library',type=Path);p.add_argument('--registry-db',type=Path);p.add_argument('--output-dir',type=Path);a=p.parse_args();lib=a.library
 roles,ready,provenance=registration_inputs(lib,a.registry_db)
 inventories={r:roles[r]['symbols'] for r in ('client','server')}
 manifests={r:roles[r]['manifest'] for r in inventories}
 lines=(lib/'recovered/client/uc.arm.asm').read_text().splitlines();names=[]
 start=next(i for i,l in enumerate(lines) if l.startswith('// _ZN8Presonus2UC12EventFactoryC1Ev '))
 for line in lines[start+1:]:
  if not line.strip():break
  if '// void Presonus::UC::EventFactory::addClass<' in line:names.append(line.split('// ',1)[1])
 assert len(names)==35 and len(set(names))==35
 entries=[]
 for name in names:
  codec=name.removeprefix('void Presonus::UC::EventFactory::addClass<').removesuffix('>()').strip()
  event=re.search(r'<Presonus::UC::([A-Za-z0-9_]+)',codec)
  event=event.group(1) if event else codec.removeprefix('Presonus::UC::').removesuffix('Class')
  records={}
  for role,inventory in inventories.items():
   registration=next(s for s in inventory if s.get('demangled')==name)
   payload=[s for s in inventory if s.get('demangled','').startswith(codec+'::') and ('::read(' in s['demangled'] or '::write(' in s['demangled'])]
   primitive=[s for s in inventory if s.get('demangled','').startswith('Presonus::UC::PrimitiveEventClass<Presonus::UC::'+event+', ') and ('::read(' in s['demangled'] or '::write(' in s['demangled'])]
   isready=lambda s:(s['mangled'],manifests[role]['sha256']) in ready
   records[role]=dict(registration=registration,registration_ready=isready(registration),
                      payload=[dict(symbol=s,portable_ready=isready(s)) for s in payload],
                      primitive_dispatch=[dict(symbol=s,portable_ready=isready(s)) for s in primitive])
  entries.append(dict(codec=codec,event=event,roles=records,
                      scope='Registration readiness comes only from SQLite admission. Constructor ABI, allocation and ownership require separate evidence; Core implementation is out of scope.'))
 report=dict(registrations=35,entries=entries,scope='Coverage tracker only, independent of function readiness totals; a portable adapter does not recover original addClass.',
             originals=manifests,readiness_registry=provenance,
             inventory_source='SQLite catalog_symbols; admission only, no unadmitted fragments')
 target=a.output_dir or lib/'validation/uc-registration';target.mkdir(parents=True,exist_ok=True)
 (target/'coverage.json').write_text(json.dumps(report,indent=2)+'\n')
 text=['# Original UC registration dependency coverage','',report['scope'],'',
 '| # | Original codec registration | Client payload ready/entries | Server payload ready/entries | Primitive dispatch ready/entries | Registration |',
 '| --- | --- | --- | --- | --- | --- |']
 for i,e in enumerate(entries,1):
  def status(items):return f"{sum(x['portable_ready'] for x in items)}/{len(items)}"
  c=e['roles']['client'];s=e['roles']['server']
  text.append(f"| {i} | `{e['codec']}` | {status(c['payload'])} | {status(s['payload'])} | {status(c['primitive_dispatch'])} per ELF | {int(c['registration_ready'])} / {int(s['registration_ready'])} |")
 text+=['','Registration shows admitted ready status for client / server from SQLite. Unadmitted does not mean declaration-pending. This generated report preserves original symbol identities and ELF provenance; it does not independently establish guarded-static, pool or constructor ABI coverage.','',
 'Completed payloads and dispatch wrappers become usable through explicitly independent portable `FactoryCodec` adapters. They do not establish original constructor, vtable, pool, layout or ARM ABI compatibility.','']
 (target/'COVERAGE.md').write_text('\n'.join(text));print('Mapped all35 original registrations for both ELFs')

if __name__=='__main__':main()
