"""Execute exact Phase07 ARM target instructions with declared provider boundaries."""
import argparse,hashlib,json,struct,itertools
from pathlib import Path
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import *
from unicorn.arm_const import *
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
IDENT={'04':(296780,240,'_ZN8Presonus5Mixer15GlobalComponent15storeMixerStateEPN4Core8Portable14IStorageFilterE'),'07':(244492,296,'_ZN8Presonus5Mixer11FXComponent4loadERKN4Core8Portable12InputStorageE'),'10':(120132,300,'_ZN8Presonus5Mixer9ParamLink7connectEPNS_24MixerClientComponentBaseE')}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def generate(path,task):
 key=task[-2:];address,size,mangled=IDENT[key];assert sha(path)==SHA
 with open(path,'rb') as f:
  e=ELFFile(f);sec=e.get_section(12);offset=sec['sh_offset']+address-sec['sh_addr'];f.seek(offset);body=f.read(size);segments=[(s['p_vaddr'],s['p_memsz'],s.data()) for s in e.iter_segments() if s['p_type']=='PT_LOAD']
 cases=[]
 inputs=([dict(filter=fil,save_result=res) for fil,res in itertools.product([0,1],[0,1])] if key=='04' else [dict(filter=fil,result=res,values=vals) for fil,res,vals in itertools.product([0,1],[0,1],[[0,0x3f800000,0xbf800000],[0x3fc00000,0xc0200000,0x42c80000]])] if key=='07' else [dict(source=src,flag=flag,found=found,client=client,old=old) for src,flag,found,client,old in itertools.product([0,1],[0,1],[0,1],[0,1],[0,1])])
 for case in inputs:
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);pages=set()
  for a,n,d in segments:
   for pg in range(a&~4095,(a+n+4095)&~4095,4096):
    if pg not in pages:u.mem_map(pg,4096);pages.add(pg)
   u.mem_write(a,d)
  u.mem_map(0x60000000,0x10000);u.mem_map(0x70000000,0x10000)
  def put(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
  def get(a):return struct.unpack('<I',u.mem_read(a,4))[0]
  def text(a):
   out=b''
   while u.mem_read(a+len(out),1)!=b'\0':out+=bytes(u.mem_read(a+len(out),1));assert len(out)<512
   return out.decode()
  calls=[];writes=[]
  if key=='04':put(0x60000088,0x60001000);put(0x60001000,0x60002000);put(0x60002024,0x60003000)
  if key=='07':
   put(0x60001020,0x60002000);put(0x60001030,0x60003000 if case['filter'] else 0)
   for i in range(3):put(0x60000100+4*i,0x60004000+0x100*i);put(0x60004000+0x100*i,0x60005000+0x100*i);put(0x60005044+0x100*i,0x60006000+0x100*i)
  if key=='10':
   put(0x60000024,0x60001000 if case['source'] else 0);put(0x60000030,0x60002000 if case['old'] else 0);u.mem_write(0x6000002c,bytes([case['flag']]));u.mem_write(0x60000004,b'gain\0');put(0x60001000,0x60004000);put(0x6000100c,0x60005000);put(0x60005000,3);put(0x60004044,0x60006000);put(0x60003000,0x60007000);put(0x60007058,0x60008000)
  def hook(m,a,n,d):
   r0=m.reg_read(UC_ARM_REG_R0);r1=m.reg_read(UC_ARM_REG_R1)
   if key=='04':
    if a==0x121dbc:calls.append('allocator');m.reg_write(UC_ARM_REG_R0,0x60004000)
    elif a==0x121a68:calls.append('attributes')
    elif a==0x117950:assert m.reg_read(UC_ARM_REG_R2)==1;calls.append('builder')
    elif a==0x60003000:
     assert r0==0x60001000 and get(r1+32)==(0x60005000 if case['filter'] else 0);calls.append('save');m.reg_write(UC_ARM_REG_R0,case['save_result'])
    elif a==0x486b4:calls.append('path');u.mem_write(r0,b'captured.scene\0')
    elif a==0x118ec8:
     assert m.reg_read(UC_ARM_REG_R2)==0 and m.reg_read(UC_ARM_REG_R3)==0;assert get(m.reg_read(UC_ARM_REG_SP))==0 and get(m.reg_read(UC_ARM_REG_SP)+4)==0;calls.append('archive')
    elif a==0x2f178:calls.append('builder_cleanup')
    elif a==0x1228b0:calls.append('attributes_cleanup')
    else:return
   elif key=='07':
    if a==0x116a38:calls.append('debug')
    elif a==0x82ecc:
     assert r0==0x60000000 and u.mem_read(0x600000e4,1)==b'\x01';assert text(r1)=='ignoreAltMemory';assert get(r1+32)==0x60002000 and get(r1+48)==(0x60003000 if case['filter'] else 0);calls.append('load');m.reg_write(UC_ARM_REG_R0,case['result'])
    elif a in [0x60006000,0x60006100,0x60006200]:
     i=(a-0x60006000)//0x100;assert u.mem_read(0x600000e4,1)==b'\x00';calls.append('value'+str(i));m.reg_write(UC_ARM_REG_R0,case['values'][i])
    else:return
   else:
    if a==0x11c2e4:assert r0==0x60002000 and r1==0x60000028;calls.append('remove')
    elif a==0x11b968:assert r0==0x60009030 and text(r1)=='gain';calls.append('lookup');m.reg_write(UC_ARM_REG_R0,0x60003000 if case['found'] else 0)
    elif a==0x60006000:calls.append('get');m.reg_write(UC_ARM_REG_R0,0x40900000)
    elif a==0x60008000:assert r0==0x60003000 and r1==0x40900000 and m.reg_read(UC_ARM_REG_R2)==0;calls.append('set')
    elif a==0x11d4f4:assert r0==0x60003000;calls.append('add')
    else:return
   m.reg_write(UC_ARM_REG_PC,m.reg_read(UC_ARM_REG_LR))
  def write(m,access,a,n,v,d):
   if 0x60000000<=a<0x60000100:writes.append([a-0x60000000,n,v])
  u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write);u.reg_write(UC_ARM_REG_R0,0x60000000);u.reg_write(UC_ARM_REG_R1,(0x60005000 if case['filter'] else 0) if key=='04' else 0x60001000 if key=='07' else 0x60009000 if case['client'] else 0);u.reg_write(UC_ARM_REG_SP,0x70008000);u.reg_write(UC_ARM_REG_LR,0x6000f000);u.emu_start(address,0x6000f000,count=5000);assert u.reg_read(UC_ARM_REG_PC)==0x6000f000
  case['calls']=calls;case['writes']=writes
  if key=='07':case['return']=u.reg_read(UC_ARM_REG_R0)
  if key=='10':case['target']=int(get(0x60000030)!=0)
  cases.append(case)
 return dict(task=task,mangled=mangled,original_elf_sha256=SHA,original_range=dict(address=address,size=size,section=12,file_offset=offset,sha256=hashlib.sha256(body).hexdigest()),cases=cases,oracle=dict(engine='Unicorn '+unicorn.__version__,producer_sha256=sha(__file__),stubs='Explicit named Core/app boundaries and virtual save/load/parameter boundaries; original app instructions and FX float-to-double conversion execute. No Core binary implementation recovered.',domain='Bounded valid receivers and named borrowed providers; original call order/args, receiver writes, outputs; no EH/concurrency/hardware. ParamLink numeric source only; string follow-up excluded.'))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--elf',required=True);p.add_argument('--task',default=Path(__file__).parent.name);p.add_argument('--out');p.add_argument('--verify');a=p.parse_args();r=generate(a.elf,a.task)
 if a.verify:assert r==json.loads(Path(a.verify).read_text());print(a.task,len(r['cases']),'native PASS')
 else:Path(a.out).write_text(json.dumps(r,indent=2)+'\n')
