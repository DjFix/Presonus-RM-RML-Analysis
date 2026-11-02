"""Verify each sealed original identity through the actual ELF section mapping."""
import argparse,hashlib,json,re
from pathlib import Path
from elftools.elf.elffile import ELFFile
ROOT=Path(__file__).resolve().parents[5]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args(); records=[]
 for i in range(1,11):
  packet=ROOT/f'temp/recovery-work/graph-live-trial-07/trial07_meter_{i}-packet'
  j=json.loads((packet/'context.json').read_text());o=j['originals'][0]['original'];elf=ROOT/'rootfs/CS18_v13840/home/root/surface';blob=elf.read_bytes();assert hashlib.sha256(blob).hexdigest()==o['elf']
  with elf.open('rb') as f:
   e=ELFFile(f);s=e.get_section(int(o['section_json']));off=s['sh_offset']+o['address']-s['sh_addr'];assert s['sh_type']!='SHT_NOBITS';assert 0<=o['address']-s['sh_addr']<=s['sh_size']-o['size']; data=blob[off:off+o['size']]
   syms=[x for x in e.get_section_by_name('.symtab').iter_symbols() if x.name==o['mangled']];assert len(syms)==1;assert syms[0]['st_value']==o['address'] and syms[0]['st_size']==o['size'] and syms[0]['st_shndx']==int(o['section_json'])
  digest=hashlib.sha256(data).hexdigest();s=(packet/'ELF_CONTEXT.md').read_text();assert re.search(r'SHA256 `'+digest+r'`',s)
  records.append(dict(original=o,file_offset=off,section=s and '.text',range_sha256=digest,packet_manifest=str((packet/'context.json').relative_to(ROOT)),packet_manifest_sha256=hashlib.sha256((packet/'context.json').read_bytes()).hexdigest()))
 Path(a.out).write_text(json.dumps({'version':1,'ranges':records},indent=2)+'\n');print('verified',len(records),'separate original ELF ranges')
if __name__=='__main__':main()
