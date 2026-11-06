"""Execute only four original application ranges. Core resize is a boundary."""
import argparse, hashlib, json, struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_PC, UC_ARM_REG_SP, UC_ARM_REG_LR
SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
PACKETS=Path('temp/recovery-work/rolling200-03/daw_maps183/prepared183/packets')
def capture():
 path=Path('rootfs/CS18_v13840/home/root/surface'); raw=path.read_bytes(); assert hashlib.sha256(raw).hexdigest()==SHA
 cases=[];ranges=[]
 with path.open('rb') as f:
  elf=ELFFile(f); symbols={s.name:s for s in elf.get_section_by_name('.symtab').iter_symbols()}
  segments=[(s['p_vaddr'],s.data()) for s in elf.iter_segments() if s['p_type']=='PT_LOAD']
  for p in sorted(PACKETS.iterdir()):
   t=json.loads((p/'request.json').read_text())['targets'][0]; a=t['address']; n=t['size'];sym=symbols[t['mangled']]; sec=elf.get_section(sym['st_shndx']); off=sec['sh_offset']+a-sec['sh_addr']
   assert (sym['st_value'],sym['st_size'])==(a,n)
   ranges.append(dict(mangled=t['mangled'],address=a,size=n,section=sec.name,file_offset=off,sha256=hashlib.sha256(raw[off:off+n]).hexdigest()))
   boundary=0x78e40 if 'TimeSignatureMap' in t['mangled'] else 0x78cc4
   for seed in [0,83,170,255]:
    for mode in ['return_false','return_true','exception_boundary']:
     u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x280000);u.mem_map(0x300000,0x10000);u.mem_map(0x900000,0x20000)
     for addr,data in segments:u.mem_write(addr,data)
     obj=0x300000; stop=0x301000;u.mem_write(obj,bytes([seed])*64);trace=[];writes=[];visited=[]
     def hook(uc,pc,size,user):
      if pc==stop:uc.emu_stop();return
      if pc==boundary:
       trace.append({'address':pc,'r0':uc.reg_read(UC_ARM_REG_R0)-obj,'r1':uc.reg_read(UC_ARM_REG_R1),'r2':uc.reg_read(UC_ARM_REG_R2),'state':bytes(uc.mem_read(obj,24)).hex()})
       if mode=='exception_boundary':uc.emu_stop();return
       uc.reg_write(UC_ARM_REG_R0,mode=='return_true');uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
      assert a<=pc<a+n,(hex(pc),t)
      visited.append(pc)
     def write(uc,access,addr,size,value,user):
      if obj<=addr<obj+64:writes.append([addr-obj,size,value])
     u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
     u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_SP,0x91f000);u.reg_write(UC_ARM_REG_LR,stop)
     u.emu_start(a,stop,count=100)
     ended=u.reg_read(UC_ARM_REG_PC);assert ended==(boundary if mode=='exception_boundary' else stop)
     cases.append(dict(mangled=t['mangled'],seed=seed,mode=mode,trace=trace,writes=writes,state=bytes(u.mem_read(obj,64)).hex(),returned_this=None if mode=='exception_boundary' else u.reg_read(UC_ARM_REG_R0)==obj,instructions=visited))
 return dict(elf_sha256=SHA,ranges=ranges,cases=cases,scope='48 exact application executions; Core resize not executed; exception mode stops at boundary and does not simulate unwinding')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();Path(a.out).write_text(json.dumps(capture(),indent=2)+'\n');print('48 native boundary observations; 4 separately verified ranges')
