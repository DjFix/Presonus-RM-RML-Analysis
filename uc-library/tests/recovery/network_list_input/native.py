"""Private-memory original application ARM oracle. Every PC is fail-closed.
Provider calls are observed boundaries; no historical Core executes.
"""
import pathlib,json,hashlib,struct,itertools
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
from elftools.elf.elffile import ELFFile
ROOT=pathlib.Path(__file__).resolve().parents[4]
BASE=ROOT/'uc-library/tests/recovery/network_list_input'
PACKETS=ROOT/'temp/recovery-work/rolling200-03/network01/prepared01/packets'
ELF=ROOT/'rootfs/CS18_v13840/home/root/surface'
SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
RAW=ELF.read_bytes();assert hashlib.sha256(RAW).hexdigest()==SHA
RANGES={}
for n in [1,2]:
 p=PACKETS/f'rolling200_03_network01_{n:02}'/'native-context.json';j=json.loads(p.read_text());b=j['bodies'][j['roots'][0]]
 with ELF.open('rb') as f:
  s=ELFFile(f).get_section(b['section_index']);off=s['sh_offset']+b['address']-s['sh_addr']
 assert off==b['file_offset'] and hashlib.sha256(RAW[off:off+b['size']]).hexdigest()==b['bytes_sha256']
 RANGES[n]={k:b[k] for k in ['address','size','file_offset','section_index','section','bytes_sha256']}
OBJ=0x400000;DATA=OBJ+0x1000;ITEM=OBJ+0x2000;OWNER=OBJ+0x3000;VIEW=OBJ+0x4000;VT=OBJ+0x5000;EV=OBJ+0x6000;STACK=0x500000;STOP=0x600000
AUDIT={'instructions':0,'unexpected':0,'Core_body_instructions_executed':0,'intercepts':{}}
def w(u,a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
def execute(inp):
 mode,a,b,c,d,e=inp;body=RANGES[mode+1];u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x300000)
 with ELF.open('rb') as f:
  for seg in ELFFile(f).iter_segments():
   if seg['p_type']=='PT_LOAD':u.mem_write(seg['p_vaddr'],seg.data())
 for addr,size in [(OBJ,0x10000),(STACK,0x10000),(STOP,0x1000)]:u.mem_map(addr,size)
 events=[]
 if mode==0:
  w(u,OBJ+4,DATA);w(u,OBJ+8,a);w(u,EV,b);w(u,EV+4,c)
  for i in range(a):w(u,DATA+4*i,VIEW+16*i);w(u,VIEW+16*i,VT+64*i);w(u,VT+64*i+0x2c,STOP+0x100+4*i)
 else:
  w(u,OBJ+0x24,DATA);w(u,OBJ+0x28,1);w(u,DATA,ITEM if e else 0);w(u,ITEM+0x80,ITEM+0x100 if d else 0);w(u,OBJ+0x38,OWNER)
 def hook(uc,pc,size,_):
  x=uc.reg_read(UC_ARM_REG_R0);y=uc.reg_read(UC_ARM_REG_R1);z=uc.reg_read(UC_ARM_REG_R2)
  if body['address']<=pc and pc+size<=body['address']+body['size']:AUDIT['instructions']+=1;return
  if mode==0 and STOP+0x100<=pc<STOP+0x100+4*a:
   i=(pc-STOP-0x100)//4;assert x==VIEW+16*i and y==EV;events.append(i+1);uc.reg_write(UC_ARM_REG_R0,(i+1)%2)
  elif mode==1 and pc==0x9f4e0:assert x==OWNER;events.append(10);uc.reg_write(UC_ARM_REG_R0,c)
  elif mode==1 and pc in [0xa1344,0xa0fbc]:
   assert x==OWNER and y==(ITEM+0x100 if d else 0);events.extend([20 if pc==0xa1344 else 30,1,z])
  elif mode==1 and pc==0x10e9fc:assert x==VIEW;events.append(40)
  else:AUDIT['unexpected']+=1;raise RuntimeError(f'unbound PC {pc:#x}')
  AUDIT['intercepts'][hex(pc)]=AUDIT['intercepts'].get(hex(pc),0)+1;uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
 u.hook_add(UC_HOOK_CODE,hook);u.reg_write(UC_ARM_REG_SP,STACK+0xf000);w(u,STACK+0xf000,e);u.reg_write(UC_ARM_REG_LR,STOP);u.reg_write(UC_ARM_REG_R0,OBJ);u.reg_write(UC_ARM_REG_R1,EV if mode==0 else a);u.reg_write(UC_ARM_REG_R2,b);u.reg_write(UC_ARM_REG_R3,VIEW)
 u.emu_start(body['address'],STOP,count=1000);assert u.reg_read(UC_ARM_REG_PC)==STOP
 return events
def generate():
 cases=[]
 for a,b,c in itertools.product(range(6),[-2147483648,-1,0,1,2147483647],[0,1]):
  inp=[0,a,b,c,0,0];cases.append({'input':inp,'expected':execute(inp)})
 for a,b,c,d,e in itertools.product([-2147483648,-1,0,1,2147483647],[0,1],[0,1,2,9],[0,1],[0,1,2,2147483647]):
  inp=[1,a,b,c,d,e];cases.append({'input':inp,'expected':execute(inp)})
 return {'version':1,'elf':str(ELF.relative_to(ROOT)),'elf_sha256':SHA,'ranges':RANGES,'audit':AUDIT,'cases':cases}
if __name__=='__main__':
 data=generate();(BASE/'fixtures.json').write_text(json.dumps(data,indent=2)+'\n');print(len(data['cases']),'original app instruction cases')
