import unicorn,elftools,platform
import hashlib,json,struct,itertools
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
ROOT=Path('/home/rs/projects/opencs/ai-line-analysis');RUN=ROOT/'temp/recovery-work/reconstruction10x10-20261116';TASK='real10_g04_s09'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def generate():
 packet=RUN/'prepared-main/packets'/TASK;req=json.loads((packet/'request.json').read_text());t=req['targets'][0];release=req['work_binding']['binary_releases'][0];binding=json.loads((RUN/'SCOPED_READ_INPUTS-remaining18_phase05-real10_g04.json').read_text())[release['original_path']];elfpath=Path(binding['frozen_read_path']);assert sha(elfpath)==t['original_elf_sha256']
 with elfpath.open('rb') as f:
  elf=ELFFile(f);section=elf.get_section(t['section']);off=section['sh_offset']+t['address']-section['sh_addr'];f.seek(off);body=f.read(t['size']);segments=[(s['p_vaddr'],s['p_memsz'],s.data()) for s in elf.iter_segments() if s['p_type']=='PT_LOAD']
 out=[]
 for message,name_kind,original_kind,controller_kind,available in itertools.product([-1,2,3,4],[0,1,2],[0,1],[0,1,2],[0,1]):
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);lo=min(a for a,b,c in segments)&~4095;hi=max(a+b for a,b,c in segments);u.mem_map(lo,(hi-lo+4095)&~4095)
  for a,b,c in segments:u.mem_write(a,c)
  r=0x3000000;p=r+0x1000;original=r+0x2000;controller=r+0x3000;stack=0x4000000;stop=0x5000000
  for a in [r,stack,stop]:u.mem_map(a,0x10000)
  put=lambda a,v:u.mem_write(a,struct.pack('<I',v&0xffffffff))
  put(p,r+0x5000);put(r+0x500c,r+0x8000);put(p+0xc,r+0x4000 if name_kind!=2 else -8);u.mem_write(r+0x4008,(b'ch_select' if name_kind==0 else b'other')+b'\0');put(r+0x6000,r+0x7000);put(r+0x7058,r+0x8004)
  u.reg_write(UC_ARM_REG_R0,r);u.reg_write(UC_ARM_REG_R1,p);u.reg_write(UC_ARM_REG_R2,message&0xffffffff);u.reg_write(UC_ARM_REG_SP,stack+0x8000);u.reg_write(UC_ARM_REG_LR,stop);trace=[];writes=[]
  def cstring(addr):
   data=bytearray()
   while True:
    c=bytes(u.mem_read(addr+len(data),1))
    if c==b'\0':return bytes(data)
    data+=c
    assert len(data)<128
  def hook(uc,addr,size,_):
   if addr==stop:uc.emu_stop();return
   args=[uc.reg_read(x) for x in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]]
   if addr==0x11c87c:
    assert args[:3]==[r,p,message&0xffffffff];trace.append('base')
   elif addr==0xb0f8:
    left,right=cstring(args[0]),cstring(args[1]);assert right==b'ch_select';trace.append('strcmp');uc.reg_write(UC_ARM_REG_R0,0 if left==right else 1)
   elif addr==r+0x8000:
    assert args[0]==p;trace.append('original');uc.reg_write(UC_ARM_REG_R0,original if original_kind else 0)
   elif addr==0x11e1d0:
    assert args[0]==original;trace.append('controller');uc.reg_write(UC_ARM_REG_R0,controller if controller_kind else 0)
   elif addr==0xae58:
    assert args[:4]==[controller,0x18ad88,0x204e28,4];trace.append('cast');uc.reg_write(UC_ARM_REG_R0,controller if controller_kind==2 else 0)
   elif addr==0x11acf0:
    assert args[:2] in [[controller,360],[r,1000]];trace.append('tag'+str(args[1]));uc.reg_write(UC_ARM_REG_R0,(r+0x9000 if available else 0) if args[1]==360 else r+0x6000)
   elif addr==r+0x8004:
    assert args[0]==r+0x6000;writes.append(dict(float_bits=args[1],edit=args[2]));trace.append('set')
   else:return
   uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,hook);u.emu_start(t['address'],stop,count=1000)
  out.append(dict(message=message,name_kind=name_kind,original_kind=original_kind,controller_kind=controller_kind,available=available,trace=trace,writes=writes))
 return dict(producer_versions=dict(python=platform.python_version(),unicorn=unicorn.__version__,pyelftools=elftools.__version__),task_id=TASK,elf_sha256=sha(elfpath),mangled=t['mangled'],section=section.name,file_offset=off,address=t['address'],size=t['size'],range_sha256=hashlib.sha256(body).hexdigest(),cases=out,oracle='Original ARM app target executes over all guarded paths. Core base/original/controller/tag APIs, libc strcmp and exact IParamObserver-to-Component RTTI cast are explicit call boundaries. Host pinned providers independently verify actual source-port type-ID adaptation and parameter edit notifications; no Core native body execution.')
if __name__=='__main__':print(json.dumps(generate(),indent=2))
