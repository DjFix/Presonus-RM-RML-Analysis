"""Original ARM application instructions; Core operations are bounded providers.
No firmware system calls, native Core recovery, device access or host pointers.
"""
import hashlib,json,pathlib,struct
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ROOT=pathlib.Path(__file__).resolve().parents[4]
ELF=ROOT/'rootfs/RML16AI_Rack_13731/home/root/mixer'
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
NAMES=['_ZN8Presonus5Panel17FxPresetComponent12paramChangedEPN4Core8Portable9ParameterEi','_ZN8Presonus5Panel15PresetComponent4initEv','_ZNK8Presonus5Panel17PresetNameManager11lookupCacheEPKc']
def generate():
 blob=ELF.read_bytes();assert hashlib.sha256(blob).hexdigest()==SHA
 f=ELF.open('rb');e=ELFFile(f);sy=e.get_section_by_name('.symtab');ranges=[]
 for name in NAMES:
  s=sy.get_symbol_by_name(name)[0];sec=e.get_section(s['st_shndx']);off=sec['sh_offset']+s['st_value']-sec['sh_addr'];ranges.append(dict(mangled=name,address=s['st_value'],size=s['st_size'],section=sec.name,section_index=s['st_shndx'],file_offset=off,sha256=hashlib.sha256(blob[off:off+s['st_size']]).hexdigest()))
 error=sy.get_symbol_by_name('_ZN4Core11ConstVectorIPN8Presonus5Panel23FXPresetRecallComponentEE5errorE')[0];assert error['st_value']==0x49452c and e.get_section(error['st_shndx'])['sh_type']=='SHT_NOBITS'
 def machine():
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x600000)
  for seg in e.iter_segments():
   if seg['p_type']=='PT_LOAD':u.mem_write(seg['p_vaddr'],seg.data())
  u.mem_map(0x1000000,0x20000);u.mem_map(0x9000000,0x10000)
  return u
 def word(u,a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def rd(u,a):return struct.unpack('<I',u.mem_read(a,4))[0]
 def text(u,a):return bytes(u.mem_read(a,256)).split(b'\0')[0].decode()
 def execute(u,start,args,hook):
  pcs=[];writes=[];stop=0x101f000
  def code(uc,pc,n,_):
   if pc==stop:uc.emu_stop();return
   if hook(uc,pc):uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
   assert any(r['address']<=pc<r['address']+r['size'] for r in ranges),hex(pc)
   pcs.append(pc)
  def write(uc,access,a,n,v,_):
   assert 0x1000000<=a<a+n<=0x1020000 or 0x9000000<=a<a+n<=0x9010000,hex(a)
   if a<0x1020000:writes.append([a,n,v])
  u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
  for reg,arg in zip([UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2],args):u.reg_write(reg,arg)
  u.reg_write(UC_ARM_REG_SP,0x9008000);u.reg_write(UC_ARM_REG_LR,stop);u.emu_start(start,stop+4,count=2000);assert u.reg_read(UC_ARM_REG_PC)==stop
  return pcs,writes
 cases=[]
 for value in (-2.,-1.,-.9,0.,1.,1.9,2.,3.,4.,100.):
  for old in (-1,0,2):
   for msg,match in ((3,1),(2,1),(3,0)):
    u=machine();obj=0x1000000;param=obj+0x1000;other=param+0x100;array=obj+0x2000;vt=obj+0x3000;pv=vt+0x100;dest=obj+0x4000;source=dest+0x100;childbase=obj+0x5000;string=obj+0x8000
    def w(a,v):word(u,a,v)
    w(obj,vt);w(param,pv);w(pv+0x44,0x1010010);w(vt+0x2c,0x1010020);w(vt+0x48,0x1010030);w(obj+0xe4,param);w(obj+0x8c,dest);w(obj+0xd0,array);w(obj+0xd4,4);w(dest,pv);w(pv+0x58,0x1010040);w(source,pv)
    for i in range(4):w(array+i*4,childbase+i*0x100);u.mem_write(childbase+i*0x100+8,(('reverb' if i<=1 else 'delay')+'\0').encode())
    w(obj+0xe8,0 if old<0 else childbase+old*0x100)
    trace=[];registrations=[];formatter='none';mirror=-1;updates=0;index=int(value);fault=False
    def hook(uc,pc):
     nonlocal formatter,mirror,updates,fault
     r0=uc.reg_read(UC_ARM_REG_R0);r1=uc.reg_read(UC_ARM_REG_R1)
     if pc==0x839b4:trace.append('base')
     elif pc==0x1010010:uc.reg_write(UC_ARM_REG_R0,struct.unpack('<I',struct.pack('<f',value if r0==param else 7.))[0])
     elif pc==0x157958:
      v=struct.unpack('<f',struct.pack('<I',r0))[0];uc.reg_write(UC_ARM_REG_R0,int(v)&0xffffffff)
     elif pc==0x110810:formatter=text(uc,r0);uc.reg_write(UC_ARM_REG_R0,0x1234)
     elif pc==0x119c4c:uc.reg_write(UC_ARM_REG_R0,dest)
     elif pc==0x5541c:uc.reg_write(UC_ARM_REG_R0,source if 0<=index<4 else 0)
     elif pc==0x1010040:
      assert uc.reg_read(UC_ARM_REG_R2)==1;mirror=int(struct.unpack('<f',struct.pack('<I',r1))[0])
     elif pc==0x1010020:
      child=rd(uc,obj+0xe8);uc.reg_write(UC_ARM_REG_R0,child+8 if child else 0x35b15c)
     elif pc==0xaf70:
      if r1==8:
       fault=True;trace.append('fault:strcmp@8');uc.reg_write(UC_ARM_REG_LR,0x101f000)
      else:
       a=text(uc,r0);b=text(uc,r1);uc.reg_write(UC_ARM_REG_R0,0 if a==b else 1)
     elif pc==0x56d40:uc.reg_write(UC_ARM_REG_R0,obj+0xa000)
     elif pc==0x84b08:
      # This call is a separately executed original target below. This FX
      # observation binds a concrete manager boundary with all three caches.
      typ=text(uc,r1);registrations.append(typ);uc.reg_write(UC_ARM_REG_R0,obj+0xb000)
     elif pc==0x56ea8:assert r1==obj+0x84
     elif pc==0x1010030:updates+=1;trace.append('name')
     elif pc==0x836dc:trace.append('edit')
     else:return False
     return True
    pcs,writes=execute(u,0x55858,[obj,param if match else other,msg],hook)
    child=rd(u,obj+0xe8);typ=text(u,child+8) if child else ''
    expected=f'{formatter}|{mirror}|{typ}|{",".join(registrations)}|{updates}|{int("edit" in trace)}|{int(fault)}\n'
    cases.append(dict(argv=[str(value),str(old),str(msg),str(match)],expected=expected,trace=trace,writes=writes,executed_pcs=pcs))
 lookups=[]
 for names in ([],[''],['reverb','delay','reverb'],['x','X','']):
  for query in (None,'','reverb','delay','X','missing'):
   u=machine();obj=0x1000000;arr=obj+0x1000;word(u,obj+8,arr);word(u,obj+12,len(names));ptr=obj+0x4000;u.mem_write(ptr,((query or '')+'\0').encode());compares=[]
   for i,name in enumerate(names):p=obj+0x2000+i*0x100;word(u,arr+4*i,p);u.mem_write(p+4,(name+'\0').encode())
   def hook(uc,pc):
    if pc!=0xaf70:return False
    a=text(uc,uc.reg_read(UC_ARM_REG_R0));b=text(uc,uc.reg_read(UC_ARM_REG_R1));compares.append([a,b]);uc.reg_write(UC_ARM_REG_R0,int(a!=b));return True
   pcs,writes=execute(u,0x84b08,[obj,0 if query is None else ptr],hook);ret=u.reg_read(UC_ARM_REG_R0);lookups.append(dict(names=names,query=query,index=-1 if not ret else (ret-obj-0x2000)//0x100,compares=compares,executed_pcs=pcs))
 inits=[]
 for registrations in ([],[0x1000084],[0x1001111,0x1000084,0x1000084],[0x1001111]):
  for capacity in (len(registrations),len(registrations)+2):
   for grow in (0,1):
    u=machine();obj=0x1000000;cache=obj+0x2000;arr=obj+0x3000;vt=obj+0x4000;word(u,obj,vt);word(u,vt+0x48,0x1010030);word(u,cache+0x150,arr);word(u,cache+0x154,len(registrations));word(u,cache+0x158,capacity)
    for i,v in enumerate(registrations):word(u,arr+4*i,v)
    trace=[]
    def hook(uc,pc):
     if pc==0x83cac:uc.reg_write(UC_ARM_REG_R0,cache)
     elif pc==0x56da8:trace.append('grow');word(uc,cache+0x158,len(registrations)+1);uc.reg_write(UC_ARM_REG_R0,grow)
     elif pc==0x1010030:trace.append('name')
     else:return False
     return True
    pcs,writes=execute(u,0x83d38,[obj],hook);count=rd(u,cache+0x154);inits.append(dict(before=registrations,capacity=capacity,grow=grow,after=[rd(u,arr+i*4) for i in range(count)],trace=trace,writes=writes,executed_pcs=pcs))
 f.close();return dict(elf_path=str(ELF.relative_to(ROOT)),elf_sha256=SHA,ranges=ranges,fallback=dict(symbol=error.name,address=error['st_value'],section='.bss',type='SHT_NOBITS',initial_value=0,assumption='Unmodified zero-initialized ConstVector error cell'),cases=cases,lookups=lookups,inits=inits,scope='Original application targets executed in Unicorn. Core numeric/formatter/strcmp/vector growth and app service/update boundaries are explicit; concrete provider behavior checked separately on host. Original return declarations, ARM layout/ABI, exceptions and hardware unproven.')
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();pathlib.Path(a.out).write_text(json.dumps(generate(),indent=2)+'\n')
