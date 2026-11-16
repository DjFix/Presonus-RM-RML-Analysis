"""Full selected app and original PageComponent getter execution."""
import hashlib,json,pathlib,struct,subprocess
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ROOT=pathlib.Path(__file__).resolve().parents[4];BASE=pathlib.Path(__file__).parent;TASK=BASE.name
SNAP=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/reconstruction10x10-20261116/prepared-main/snapshot')
PACKET=ROOT/'temp/recovery-work/reconstruction10x10-20261116/prepared-main/packets'/TASK
EXP=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/reconstruction10x10-20261116/expansions/bound-20261116T055348/g03-page-tag/native-context.json')
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def generate(exe):
 target=json.loads((PACKET/'request.json').read_text())['targets'][0];ev=SNAP/('temp/recovery-work/reconstruction10x10-20261116/native/'+TASK+'.json');body=json.loads(ev.read_text())['body'];helper=next(v for v in json.loads(EXP.read_text())['bodies'].values() if v['address']==0x64660)
 elf=SNAP/'rootfs/CS18_v13840/home/root/surface';assert sha(elf)==target['original_elf_sha256'];raw=elf.read_bytes();ranges=[body,helper]
 with elf.open('rb') as f:
  e=ELFFile(f)
  for b in ranges:
   sec=e.get_section(b['section_index']);assert sec.name==b['section'];assert sec['sh_offset']+b['address']-sec['sh_addr']==b['file_offset'];assert hashlib.sha256(raw[b['file_offset']:b['file_offset']+b['size']]).hexdigest()==b['bytes_sha256']
 inputs=[[n,q,mask,*tags] for n in range(4) for q in [-2147483648,-1000,-1,0,7,14,2147483647] for mask in range(1<<n) for tags in [[7,14,7],[-1000,-1,0],[2147483647,0,-2147483648]]];payload=''.join(' '.join(map(str,x))+'\n' for x in inputs);provider=subprocess.check_output([str(exe),'provider'],input=payload.encode()).decode().splitlines();assert len(provider)==len(inputs);cases=[]
 for inp,line in zip(inputs,provider):
  n,q,mask,*tags=inp;observed=list(map(int,line.split()));assert observed==[v for i in range(n) for v in [int(bool(mask&(1<<i))),tags[i]]]
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  for addr in {body['address']&~4095,helper['address']&~4095,0x1000000,0x1100000,0x1200000,0x1300000}:u.mem_map(addr,4096)
  for b in ranges:u.mem_write(b['address'],raw[b['file_offset']:b['file_offset']+b['size']])
  obj=0x1000000;stop=0x1200000;sites=[];writes=[];calls=[];array=obj+0x100;vt=obj+0x200
  def w(p,v):u.mem_write(p,struct.pack('<I',v&0xffffffff))
  w(obj+0x58,array);w(obj+0x5c,n);w(vt,0x1300000)
  for i in range(n):
   child=obj+0x300+i*0x200;page=child+0x100;w(array+4*i,child);w(child,vt);w(page+0x8c,tags[i])
  before=bytes(u.mem_read(obj,4096))
  def hook(uc,a,size,user):
   if a==0x1300000:
    child=uc.reg_read(UC_ARM_REG_R0);i=(child-obj-0x300)//0x200;assert i in range(n) and child==obj+0x300+i*0x200;assert uc.reg_read(UC_ARM_REG_R1)==1348560741;casts=observed[2*i];calls.append(['actual-child-cast',i,casts]);uc.reg_write(UC_ARM_REG_R0,child+0x100 if casts else 0);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
   assert any(b['address']<=a<a+size<=b['address']+b['size'] for b in ranges),hex(a);sites.append(a)
  def write(uc,access,a,size,v,user):
   if obj<=a<a+size<=obj+4096:writes.append([a-obj,size,v])
  u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
  for r,v in [(UC_ARM_REG_SP,0x1100800),(UC_ARM_REG_LR,stop),(UC_ARM_REG_R0,obj),(UC_ARM_REG_R1,q&0xffffffff)]:u.reg_write(r,v)
  u.emu_start(body['address'],stop,count=350);assert u.reg_read(UC_ARM_REG_PC)==stop;assert not writes and before==bytes(u.mem_read(obj,4096));ret=u.reg_read(UC_ARM_REG_R0);index=-1 if ret==0 else (ret-obj-0x400)//0x200
  cases.append(dict(input=inp,expected=str(index),provider=line,native_calls=calls,native_instructions=sites,object_writes=writes))
 return dict(producer={'path':str(BASE.relative_to(ROOT)/'native.py'),'sha256':sha(__file__),'unicorn_version':__import__('unicorn').__version__,'method':'independent original ARM instruction execution and separately observed source providers'},case_count=len(cases),elf_sha256=target['original_elf_sha256'],target_range={k:body[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']},helper_ranges=[{k:helper[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']}],cases=cases,scope='Empty and 1..3 actual CCL children; page/nonpage cast patterns; signed extremes and duplicate tags. Full original lookup and PageComponent getter execute; indirect casts are explicit bridges to independently observed actual test PageChild cast provider. Real CCL child collection/ownership executes in C++; first-match identity is compared. No null children (CCL addChild requires nonnull), concurrent mutation, original return/layout/ABI or hardware claim.')
