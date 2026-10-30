#!/usr/bin/env python3
"""Map original constructor registration coverage without reconstructing Core."""
import argparse,hashlib,json,re
from pathlib import Path

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('library',type=Path);a=p.parse_args();lib=a.library
 inventories={r:json.loads((lib/'recovered'/r/'all-symbols.json').read_text()) for r in ('client','server')}
 ready=set();inputs=[lib/'validation/ready-functions.json',*sorted(lib.glob('validation/uc-*/ready-functions.fragment.json'))]
 for fragment in inputs:
  ready.update((s['mangled'],s['original_elf_sha256']) for s in json.loads(fragment.read_text())['functions'])
 manifests={r:json.loads((lib/'recovered'/r/'manifest.json').read_text()) for r in inventories}
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
                      pending='Original registration/static initialization, constructor ABI, allocation and ownership remain pending; Core implementation is out of scope.'))
 report=dict(registrations=35,entries=entries,scope='Coverage tracker only, independent of function readiness totals; a portable adapter does not recover original addClass.',
             originals=manifests,readiness_inputs={str(f.relative_to(lib)):hashlib.sha256(f.read_bytes()).hexdigest() for f in inputs},
             inventory_sha256={r:hashlib.sha256((lib/'recovered'/r/'all-symbols.json').read_bytes()).hexdigest() for r in inventories})
 target=lib/'validation/uc-registration';target.mkdir(parents=True,exist_ok=True)
 (target/'coverage.json').write_text(json.dumps(report,indent=2)+'\n')
 text=['# Original UC registration dependency coverage','',report['scope'],'',
 '| # | Original codec registration | Client payload ready/entries | Server payload ready/entries | Primitive dispatch ready/entries | Registration |',
 '| --- | --- | --- | --- | --- | --- |']
 for i,e in enumerate(entries,1):
  def status(items):return f"{sum(x['portable_ready'] for x in items)}/{len(items)}"
  c=e['roles']['client'];s=e['roles']['server']
  text.append(f"| {i} | `{e['codec']}` | {status(c['payload'])} | {status(s['payload'])} | {status(c['primitive_dispatch'])} per ELF | pending |")
 text+=['','All 35 original `addClass` methods, their guarded statics and codec construction remain pending. Original pools and Core containers are not implemented. The source JSON preserves exact original symbol identities/addresses/sizes and ELF manifests for both firmware versions.','',
 'Completed payloads and dispatch wrappers become usable through explicitly independent portable `FactoryCodec` adapters. They do not establish original constructor, vtable, pool, layout or ARM ABI compatibility.','']
 (target/'COVERAGE.md').write_text('\n'.join(text));print('Mapped all35 original registrations for both ELFs')

if __name__=='__main__':main()
