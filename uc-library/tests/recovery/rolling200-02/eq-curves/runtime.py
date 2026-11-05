"""Minimal exact ARM provider loader adapted from hash-bound runtime_math.py.
Maps role libm with recorded relocations; unresolved imports trap. No system
calls, Core body or invented host-math results are permitted.
"""
import hashlib,struct
from elftools.elf.elffile import ELFFile

def load(u,root,app,raw):
 base,rtld=0x50000000,0x60000000
 math=root/'rootfs/CS18_v13840/lib/libm-2.9.so';loader=math.parent/'ld-2.9.so'
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 with loader.open('rb') as f:
  elf=ELFFile(f);sym=next(s for s in elf.get_section_by_name('.dynsym').iter_symbols() if s.name=='_rtld_global_ro');sec=elf.get_section(sym['st_shndx']);data=sec.data()[sym['st_value']-sec['sh_addr']:][:sym['st_size']]
 u.mem_map(rtld,4096);u.mem_write(rtld,data);u.mem_write(rtld+0x40,b'\0'*8)
 definitions={};ranges=[];relocations=[];unresolved=[]
 with math.open('rb') as f:
  elf=ELFFile(f);mapped=set()
  for seg in elf.iter_segments():
   if seg['p_type']!='PT_LOAD':continue
   start=base+seg['p_vaddr'];end=start+seg['p_memsz']
   for page in range(start&~4095,(end+4095)&~4095,4096):
    if page not in mapped:u.mem_map(page,4096);mapped.add(page)
   u.mem_write(start,seg.data())
   if seg['p_flags']&1:ranges.append({'address':start,'size':end-start,'kind':'role-libm-executable-segment','file_offset':seg['p_offset'],'bytes_sha256':hashlib.sha256(seg.data()).hexdigest()})
  for sym in elf.get_section_by_name('.dynsym').iter_symbols():
   if sym['st_shndx']!='SHN_UNDEF':definitions[sym.name]=base+sym['st_value']
  for sec in elf.iter_sections():
   if sec['sh_type']!='SHT_REL':continue
   table=elf.get_section(sec['sh_link'])
   for rel in sec.iter_relocations():
    sym=table.get_symbol(rel['r_info_sym']);address=base+rel['r_offset'];prior=struct.unpack('<I',u.mem_read(address,4))[0];kind=rel['r_info_type']
    if kind==23:value=(base+prior)&0xffffffff
    elif kind in [21,22]:
     if sym['st_shndx']!='SHN_UNDEF':value=base+sym['st_value']
     elif sym.name=='_rtld_global_ro':value=rtld
     elif sym['st_info']['bind']=='STB_WEAK':value=0
     else:value=0x70000000+len(unresolved)*4096;unresolved.append({'name':sym.name,'trap':value})
    else:raise AssertionError(('unsupported relocation',kind))
    u.mem_write(address,struct.pack('<I',value));relocations.append({'offset':rel['r_offset'],'kind':kind,'symbol':sym.name,'value':value})
 bindings=[]
 with app.open('rb') as f:
  elf=ELFFile(f)
  for sec in elf.iter_sections():
   if sec['sh_type']!='SHT_REL':continue
   table=elf.get_section(sec['sh_link'])
   for rel in sec.iter_relocations():
    sym=table.get_symbol(rel['r_info_sym'])
    if sym.name not in ['pow','tanf','sinf','cosf','sqrtf','sincosf','log10f']:continue
    assert rel['r_info_type']==22
    u.mem_write(rel['r_offset'],struct.pack('<I',definitions[sym.name]));ranges.append({'address':sym['st_value'],'size':12,'kind':'math-PLT','symbol':sym.name,'file_offset':sym['st_value']-0x8000,'bytes_sha256':hashlib.sha256(raw[sym['st_value']-0x8000:sym['st_value']-0x8000+12]).hexdigest()});bindings.append({'name':sym.name,'plt':sym['st_value'],'got':rel['r_offset'],'target':definitions[sym.name]})
  for sym in elf.get_section_by_name('.symtab').iter_symbols():
   name=sym.name
   if not sym['st_size'] or not isinstance(sym['st_shndx'],int):continue
   if not (name.startswith('__aeabi_') or name.startswith('__') and name.endswith(('sf3','df3','sf2','df2'))):continue
   sec=elf.get_section(sym['st_shndx']);offset=sec['sh_offset']+sym['st_value']-sec['sh_addr'];ranges.append({'address':sym['st_value'],'size':sym['st_size'],'kind':'original-compiler-runtime','symbol':name,'file_offset':offset,'section':sec.name,'bytes_sha256':hashlib.sha256(raw[offset:offset+sym['st_size']]).hexdigest()})
 return ranges,{'math':str(math.relative_to(root)),'math_sha256':sha(math),'loader':str(loader.relative_to(root)),'loader_sha256':sha(loader),'injected_capability_word':0,'loader_read_domain':[rtld+0x40,rtld+0x48],'bindings':bindings,'relocations':relocations,'unresolved_import_traps':unresolved,'limitations':'Software-FENV capability bit clear injected test environment, not boot/HWCAP evidence. Exact role ARM runtime and libm; no syscalls, Core bodies or host math.'}
