import hashlib,json,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
ROOT=Path('/home/rs/projects/opencs/ai-line-analysis');RUN=ROOT/'temp/recovery-work/reconstruction10x10-20261116';TASK='real10_g04_s08'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def generate():
 packet=RUN/'prepared-main/packets'/TASK;req=json.loads((packet/'request.json').read_text());t=req['targets'][0];release=req['work_binding']['binary_releases'][0];binding=json.loads((RUN/'READ_INPUTS-prepared-main-real10_g04.json').read_text())[release['original_path']];elfpath=Path(binding['frozen_read_path']);assert sha(elfpath)==t['original_elf_sha256']
 with elfpath.open('rb') as f:
  elf=ELFFile(f);section=elf.get_section(t['section']);off=section['sh_offset']+t['address']-section['sh_addr'];f.seek(off);body=f.read(t['size']);segments=[(s['p_vaddr'],s['p_memsz'],s.data()) for s in elf.iter_segments() if s['p_type']=='PT_LOAD']
 out=[]
 for provider,parameter,bits in [(False,False,0),(True,False,0)]+[(True,True,x) for x in [0,0x80000000,0x3f800000,0xbf800000,0x7f800000,0xff800000,0x7fc00000,1,0x80000001]]:
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);lo=min(a for a,b,c in segments)&~4095;hi=max(a+b for a,b,c in segments);u.mem_map(lo,(hi-lo+4095)&~4095)
  for a,b,c in segments:u.mem_write(a,c)
  r=0x3000000;stack=0x4000000;stop=0x5000000
  for a in [r,stack,stop]:u.mem_map(a,0x10000)
  put=lambda a,v:u.mem_write(a,struct.pack('<I',v))
  put(r,2002816+8);put(r+0xe8,r+0x1000 if provider else 0);put(r+0x1000,r+0x3100);put(r+0x2000,r+0x3200);put(r+0x310c,r+0x4000);put(r+0x3244,r+0x4004)
  u.reg_write(UC_ARM_REG_R0,r);u.reg_write(UC_ARM_REG_SP,stack+0x8000);u.reg_write(UC_ARM_REG_LR,stop);trace=[];runtime_instructions=[]
  def hook(uc,addr,size,_):
   if addr==stop:uc.emu_stop()
   elif addr in [r+0x4000,r+0x4004,0xb4368]:
    args=[uc.reg_read(UC_ARM_REG_R0),uc.reg_read(UC_ARM_REG_R1)]
    if addr==r+0x4000:
     assert args==[r+0x1000,12];trace.append('tag12');uc.reg_write(UC_ARM_REG_R0,r+0x2000 if parameter else 0)
    elif addr==r+0x4004:
     assert args[0]==r+0x2000;trace.append('value');uc.reg_write(UC_ARM_REG_R0,bits)
    else:
     assert args[0]==r;trace.append('PresetsPageComponent::recall')
    uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
   elif not t['address']<=addr<t['address']+t['size']:runtime_instructions.append(addr)
  u.hook_add(UC_HOOK_CODE,hook);u.emu_start(t['address'],stop,count=10000)
  out.append(dict(provider=provider,parameter=parameter,float_bits=bits,trace=trace,compiler_runtime_instruction_count=len(runtime_instructions),compiler_runtime_range=dict(start=min(runtime_instructions),size=max(runtime_instructions)-min(runtime_instructions)+4,sha256=hashlib.sha256(bytes(u.mem_read(min(runtime_instructions),max(runtime_instructions)-min(runtime_instructions)+4))).hexdigest()) if runtime_instructions else None))
 return dict(task_id=TASK,elf_sha256=sha(elfpath),mangled=t['mangled'],section=section.name,file_offset=off,address=t['address'],size=t['size'],range_sha256=hashlib.sha256(body).hexdigest(),cases=out,oracle='Original application ARM range plus original compiler runtime __aeabi_fcmpgt executed; provider virtual getParameter/getValue and exact primary-table PresetsPageComponent::recall are explicit controlled boundaries, not native Core execution')
if __name__=='__main__':print(json.dumps(generate(),indent=2))
