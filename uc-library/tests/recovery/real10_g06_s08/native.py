"""Execute exact ParamLink constructor variant with explicit app/Core boundaries."""
import argparse,hashlib,json,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import *
from unicorn.arm_const import *
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def generate(path,task):
 variant,address={'real10_g06_s08':('C1',119508),'real10_g06_s09':('C2',119592)}[task];assert sha(path)==SHA
 with open(path,'rb') as f:
  e=ELFFile(f);s=e.get_section(12);offset=s['sh_offset']+address-s['sh_addr'];f.seek(offset);body=f.read(84)
 cases=[]
 for present in [False,True]:
  for flag in [False,True]:
   for name in ['', 'abcdefghijklmnopqrstuvwxyz0123456789LONG']:
    u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(address&~4095,4096);u.mem_write(address,body);u.mem_map(0x60000000,0x10000);u.mem_map(0x70000000,0x10000)
    # Boundaries must be mapped for instruction-fetch hooks.
    for a in [0x1d230,0x11d4f4]:
     if a&~4095!=address&~4095:u.mem_map(a&~4095,4096)
    u.mem_write(0x60002000,name.encode()+b'\0');calls=[];writes=[]
    def hook(m,a,n,d):
     if a==0x1d230:
      assert [m.reg_read(r) for r in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2]]==[0x60000000,0x60001000 if present else 0,0x60002000];calls.append('base');m.mem_write(0x60000024,struct.pack('<I',0x60001000 if present else 0))
     elif a==0x11d4f4:
      assert [m.reg_read(r) for r in [UC_ARM_REG_R0,UC_ARM_REG_R1]]==[0x60001000,0x60000028];calls.append('addObserver')
     else:return
     m.reg_write(UC_ARM_REG_PC,m.reg_read(UC_ARM_REG_LR))
    def write(m,access,a,n,v,d):
     if not 0x70000000<=a<a+n<=0x70010000:writes.append([a-0x60000000,n,v])
    u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write);u.reg_write(UC_ARM_REG_R0,0x60000000);u.reg_write(UC_ARM_REG_R1,0x60001000 if present else 0);u.reg_write(UC_ARM_REG_R2,0x60002000);u.reg_write(UC_ARM_REG_R3,int(flag));u.reg_write(UC_ARM_REG_SP,0x70008000);u.reg_write(UC_ARM_REG_LR,0x6000f000);u.emu_start(address,0x6000f000,count=100)
    assert u.reg_read(UC_ARM_REG_PC)==0x6000f000 and u.reg_read(UC_ARM_REG_R0)==0x60000000
    get=lambda o:struct.unpack('<I',u.mem_read(0x60000000+o,4))[0]
    cases.append(dict(present=present,flag=flag,name=name,calls=calls,flag_written=u.mem_read(0x6000002c,1)[0],target=get(0x30),writes=writes))
 return dict(task=task,variant=variant,mangled='_ZN8Presonus5Mixer9ParamLink'+variant+'EPN4Core8Portable9ParameterEPKcb',original_elf_sha256=SHA,original_range=dict(address=address,size=84,section=12,file_offset=offset,sha256=hashlib.sha256(body).hexdigest()),cases=cases,oracle=dict(engine='Unicorn '+unicorn.__version__,producer_sha256=sha(__file__),stubs=['canonical ControlMapping constructor boundary installs borrowed parameter at observed offset0x24','CCL Parameter::addObserver boundary'],domain='8 cases null/non-null parameter, both bool values, empty/long name; original call order/args, null target, bool field, vtables and receiver return observed; source-port base truncation/observer allocation tested separately'))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--elf',required=True);p.add_argument('--task',default=Path(__file__).parent.name);p.add_argument('--out');p.add_argument('--verify');a=p.parse_args();r=generate(a.elf,a.task)
 if a.verify:assert r==json.loads(Path(a.verify).read_text());print(a.task,'native8 PASS')
 else:Path(a.out).write_text(json.dumps(r,indent=2)+'\n')
