import unicorn,elftools,platform
import hashlib,json,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
ROOT=Path('/home/rs/projects/opencs/ai-line-analysis');RUN=ROOT/'temp/recovery-work/reconstruction10x10-20261116';TASK='real10_g04_s07'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def generate():
 packet=RUN/'prepared-main/packets'/TASK;req=json.loads((packet/'request.json').read_text());t=req['targets'][0];release=req['work_binding']['binary_releases'][0];binding=json.loads((RUN/'SCOPED_READ_INPUTS-remaining18_phase05-real10_g04.json').read_text())[release['original_path']];elfpath=Path(binding['frozen_read_path']);assert sha(elfpath)==t['original_elf_sha256']
 with elfpath.open('rb') as f:
  elf=ELFFile(f);section=elf.get_section(t['section']);off=section['sh_offset']+t['address']-section['sh_addr'];f.seek(off);body=f.read(t['size']);segments=[(s['p_vaddr'],s['p_memsz'],s.data()) for s in elf.iter_segments() if s['p_type']=='PT_LOAD'];helper_ranges=[]
  for address,name in [(0x3c8bc,'doUpdates'),(0x3c8cc,'postDoUpdates')]:
   file_offset=section['sh_offset']+address-section['sh_addr'];f.seek(file_offset);helper_ranges.append(dict(name=name,address=address,file_offset=file_offset,size=16,sha256=hashlib.sha256(f.read(16)).hexdigest()))
 out=[]
 for pending in [0,1,255]:
  for mutation in [-1,0,1,255]:
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM);lo=min(a for a,b,c in segments)&~4095;hi=max(a+b for a,b,c in segments);u.mem_map(lo,(hi-lo+4095)&~4095)
   for a,b,c in segments:u.mem_write(a,c)
   r=0x3000000;stack=0x4000000;stop=0x5000000
   for a in [r,stack,stop]:u.mem_map(a,0x10000)
   put=lambda a,v:u.mem_write(a,struct.pack('<I',v))
   put(r,3501792+8);u.mem_write(r+0x85,bytes([pending]));u.reg_write(UC_ARM_REG_R0,r);u.reg_write(UC_ARM_REG_SP,stack+0x8000);u.reg_write(UC_ARM_REG_LR,stop);trace=[]
   def hook(uc,addr,size,_):
    if addr==stop:uc.emu_stop()
    elif addr==0x1196a8:
     assert uc.reg_read(UC_ARM_REG_R0)==r;trace.append('C')
     if mutation>=0:uc.mem_write(r+0x85,bytes([mutation]))
     uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
    elif addr in [0x3c8bc,0x3c8cc]:
     assert bytes(uc.mem_read(r+0x85,1))==b'\0';trace.append('D' if addr==0x3c8bc else 'P')
   u.hook_add(UC_HOOK_CODE,hook);u.emu_start(t['address'],stop,count=1000)
   out.append(dict(pending=pending,mutation=mutation,trace=''.join(trace),final_pending=bytes(u.mem_read(r+0x85,1))[0]))
 return dict(producer_versions=dict(python=platform.python_version(),unicorn=unicorn.__version__,pyelftools=elftools.__version__),task_id=TASK,elf_sha256=sha(elfpath),mangled=t['mangled'],section=section.name,file_offset=off,address=t['address'],size=t['size'],range_sha256=hashlib.sha256(body).hexdigest(),helper_ranges=helper_ranges,cases=out,oracle='Original RM13731 ARM onIdle and both exact 16-byte app helper bodies execute. Receiver uses original Targeted primary table+8. Core onIdle is a controlled child-dispatch/mutation boundary; pinned host provider is independently replayed.')
if __name__=='__main__':print(json.dumps(generate(),indent=2))
