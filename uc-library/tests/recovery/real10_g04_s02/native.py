import hashlib,json,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
ROOT=Path('/home/rs/projects/opencs/ai-line-analysis')
RUN=ROOT/'temp/recovery-work/reconstruction10x10-20261116'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def generate(task):
 packet=RUN/'prepared-main/packets'/task
 req=json.loads((packet/'request.json').read_text());t=req['targets'][0]
 release=req['work_binding']['binary_releases'][0];binding=json.loads((RUN/'READ_INPUTS-prepared-main-real10_g04.json').read_text())[release['original_path']]
 elfpath=Path(binding['frozen_read_path']);assert sha(elfpath)==t['original_elf_sha256']
 with elfpath.open('rb') as f:
  elf=ELFFile(f);section=elf.get_section(t['section']);off=section['sh_offset']+t['address']-section['sh_addr'];f.seek(off);body=f.read(t['size']);segments=[(s['p_vaddr'],s['p_memsz'],s.data()) for s in elf.iter_segments() if s['p_type']=='PT_LOAD']
 out=[]
 for fill in [0,0x55,0xff]:
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);lo=min(a for a,b,c in segments)&~4095;hi=max(a+b for a,b,c in segments);u.mem_map(lo,(hi-lo+4095)&~4095)
  for a,b,c in segments:u.mem_write(a,c)
  receiver=0x3000000;stack=0x4000000;stop=0x5000000
  for a in [receiver,stack,stop]:u.mem_map(a,0x10000)
  u.mem_write(receiver,bytes([fill])*512);u.reg_write(UC_ARM_REG_R0,receiver);u.reg_write(UC_ARM_REG_SP,stack+0x8000);u.reg_write(UC_ARM_REG_LR,stop)
  trace=[]
  base=0x11a53c if task.endswith('06') else 0x11b5e0;delete=0xac10 if task.endswith('06') else 0xad5c
  def hook(uc,addr,size,_):
   if addr==stop:uc.emu_stop()
   elif addr in [base,delete]:
    arg=uc.reg_read(UC_ARM_REG_R0);trace.append(dict(call='ccl-component-destructor-boundary' if addr==base else 'operator-delete-boundary',receiver_offset=arg-receiver,state_hex=bytes(uc.mem_read(receiver,192)).hex()));uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,hook);u.emu_start(t['address'],stop,count=1000)
  assert [x['call'] for x in trace]==['ccl-component-destructor-boundary','operator-delete-boundary'];assert all(x['receiver_offset']==0 for x in trace)
  out.append(dict(initial_fill=fill,trace=trace,returned_receiver=u.reg_read(UC_ARM_REG_R0)==receiver))
 return dict(task_id=task,elf_sha256=sha(elfpath),mangled=t['mangled'],section=section.name,file_offset=off,address=t['address'],size=t['size'],range_sha256=hashlib.sha256(body).hexdigest(),cases=out,oracle='Unicorn executes exact original ARM application range; CCL destructor and allocator are explicit opaque call boundaries, not executed native provider bodies')
if __name__=='__main__':
 import sys
 print(json.dumps(generate(sys.argv[1]),indent=2))
