import hashlib,json,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
CONFIG={'elf': '/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared05/snapshot/rootfs/CS18_v13840/home/root/surface', 'sha': '304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0', 'mangled': '_ZN8Presonus7Surface11ControlNameC1EPKci', 'start': 573012, 'size': 56, 'name': True, 'call': 308348}

def observations():
 c=CONFIG; data=Path(c['elf']).read_bytes(); assert hashlib.sha256(data).hexdigest()==c['sha']
 with open(c['elf'],'rb') as f:
  e=ELFFile(f); symbols=e.get_section_by_name('.symtab').get_symbol_by_name(c['mangled']); s=next(s for s in symbols if s['st_value']==c['start'] and s['st_size']==c['size']); sec=e.get_section(s['st_shndx']); offset=sec['sh_offset']+c['start']-sec['sh_addr']; assert sec.name=='.text'
 code=data[offset:offset+c['size']]; cases=[]
 format_address=0x19e378
 with open(c['elf'],'rb') as f:
  e=ELFFile(f); section=next(s for s in e.iter_sections() if s['sh_type']!='SHT_NOBITS' and s['sh_addr']<=format_address and format_address+8<=s['sh_addr']+s['sh_size'])
  format_offset=section['sh_offset']+format_address-section['sh_addr']
  format_bytes=data[format_offset:format_offset+8]; assert format_bytes==b'%s_%02d\0'
  format_evidence=dict(address=format_address,size=8,file_offset=format_offset,section=section.name,bytes_hex=format_bytes.hex(),sha256=hashlib.sha256(format_bytes).hexdigest())
 for param in [0,0x200800]:
  for text in ['', 'gain', 'x'*31, 'x'*32, 'x'*80]:
   for index in ([-2,-1,0,9,2147483647] if c['name'] else [0]):
    u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
    for a in set([c['start']&~4095,c['call']&~4095,0x200000,0x300000,0x400000]):u.mem_map(a,4096)
    u.mem_write(c['start'],code); u.mem_write(0x200000,bytes([0xa5])*128);u.mem_write(0x200400,text.encode()+b'\0')
    for r,v in [(UC_ARM_REG_R0,0x200000),(UC_ARM_REG_R1,0x200400 if c['name'] else param),(UC_ARM_REG_R2,index&0xffffffff if c['name'] else 0x200400),(UC_ARM_REG_SP,0x300f00),(UC_ARM_REG_LR,0x400000)]:u.reg_write(r,v)
    events=[]
    def hook(uc,pc,size,_):
     if pc==0x400000:uc.emu_stop();return
     if pc==c['call']:
      events.append([uc.reg_read(r) for r in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]])
      # External Core boundary does not execute firmware. Capture arguments only.
      uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
     assert c['start']<=pc<c['start']+c['size']-4,hex(pc)
    u.hook_add(UC_HOOK_CODE,hook);u.emu_start(c['start'],0,count=100)
    assert u.reg_read(UC_ARM_REG_PC)==0x400000, 'native did not reach return sentinel'
    assert len(events)==1
    assert u.reg_read(UC_ARM_REG_R0)==0x200000
    if c['name']:
     assert events[0][1]==format_address, 'format pointer differs from section-verified original'
     assert events[0][0]==0x200000 and events[0][2]==0x200400 and events[0][3]==(index+1)&0xffffffff
     assert bytes(u.mem_read(0x200000,1))==b'\0'
    else:
     assert events[0][0]==0x200004 and events[0][1]==0x200400
     assert struct.unpack('<I',u.mem_read(0x200024,4))[0]==param
    cases.append(dict(text=text,parameter=param,index=index,events=events,return_pc=u.reg_read(UC_ARM_REG_PC),memory=bytes(u.mem_read(0x200000,40)).hex()))
 return dict(elf_sha256=c['sha'],address=c['start'],size=c['size'],file_offset=offset,section='.text',range_sha256=hashlib.sha256(code).hexdigest(),format_evidence=format_evidence,cases=cases,limitations='Core provider is an explicit call boundary; no Core firmware executed; memory outside app writes retains sentinel.')
if __name__=='__main__':print(json.dumps(observations(),indent=2))
