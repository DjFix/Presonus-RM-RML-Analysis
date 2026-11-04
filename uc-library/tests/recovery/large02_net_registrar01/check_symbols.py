import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--driver',required=True);a=p.parse_args()
symbols={x.split()[-1] for x in subprocess.check_output(['nm','--defined-only',a.driver],text=True).splitlines() if x.split()}
base=Path('temp/recovery-work/large02-network-owning03/batch02/packets')
originals=set()
for i in range(1,9):
 j=json.loads((base/f'large02_net_registrar01_{i:02}'/'request.json').read_text())
 originals.update(x['mangled'] for x in j['targets'])
assert originals <= symbols, sorted(originals-symbols)
print(json.dumps({'format':'ELF, no object decoration','verified_original_symbols':sorted(originals),'host_variants_may_alias':True},indent=2))
# Independently recompute each symbol's actual ELF section mapping and range.
import hashlib
from elftools.elf.elffile import ELFFile
fixture=json.loads(Path('uc-library/tests/recovery/large02_net_registrar01/fixtures.json').read_text())
for row in fixture['ranges']:
 o=row['original'];path=Path('rootfs/CS18_v13840/home/root/surface' if o['role']=='client' else 'rootfs/RML16AI_Rack_13731/home/root/mixer')
 raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==o['elf']
 with path.open('rb') as f:
  elf=ELFFile(f);matches=[s for s in elf.get_section_by_name('.symtab').iter_symbols() if s.name==o['mangled']]
  assert len(matches)==1
  s=matches[0];assert s['st_value']==o['address'] and s['st_size']==o['size']
  section=elf.get_section(s['st_shndx']);assert section.name==row['section'] and section['sh_type']!='SHT_NOBITS'
  assert section['sh_addr']<=o['address'] and o['address']+o['size']<=section['sh_addr']+section['sh_size']
  offset=section['sh_offset']+o['address']-section['sh_addr'];assert offset==row['file_offset']
  assert hashlib.sha256(raw[offset:offset+o['size']]).hexdigest()==row['bytes_sha256']
print('independent actual ELF section/range audits',len(fixture['ranges']))
