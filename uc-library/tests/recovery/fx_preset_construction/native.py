"""Offline execution of exact application ranges; CCL calls are typed boundaries.
No Core implementation recovered or executed, and no hardware/syscalls passed.
"""
import hashlib,json,pathlib,struct
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ROOT=pathlib.Path(__file__).resolve().parents[4]
ELF=ROOT/'rootfs/RML16AI_Rack_13731/home/root/mixer'
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
BASE='_ZN8Presonus5Panel15PresetComponentC2EPKcS3_S3_RNS_5Mixer18MixerComponentBaseE'
FX='_ZN8Presonus5Panel17FxPresetComponentC{}ERNS0_19FrontPanelComponentERNS_5Mixer18MixerComponentBaseE'
def digest(b):return hashlib.sha256(b).hexdigest()
def generate():
 blob=ELF.read_bytes();assert digest(blob)==SHA
 with ELF.open('rb') as f:
  e=ELFFile(f);tab=e.get_section_by_name('.symtab');ranges=[];targets={}
  for name in [BASE,FX.format(1),FX.format(2)]:
   s=tab.get_symbol_by_name(name)[0];sec=e.get_section(s['st_shndx']);a=s['st_value'];n=s['st_size'];off=sec['sh_offset']+a-sec['sh_addr'];targets[name]=(a,n)
   ranges.append(dict(mangled=name,address=a,size=n,section=sec.name,section_index=s['st_shndx'],file_offset=off,sha256=digest(blob[off:off+n])))
  def filebytes(a,n):
   for sec in e.iter_sections():
    if sec['sh_type']!='SHT_NOBITS' and sec['sh_addr']<=a and a+n<=sec['sh_addr']+sec['sh_size']:
     off=sec['sh_offset']+a-sec['sh_addr'];return blob[off:off+n]
   raise AssertionError(hex(a))
  def text(a):return filebytes(a,100).split(b'\0',1)[0].decode()
  table=filebytes(0x3570a0,336);assert digest(table)=='7e6035e0be873afbc9e4333aecf287cc30adba188e8d8a57845034b389576587'
  params=[]
  for i in range(4):
   b=table[i*84:(i+1)*84];typ,tag=struct.unpack_from('<II',b);nums=struct.unpack_from('<fffff',b,40);flags,unit,curve,strings,title,short=struct.unpack_from('<IIIIII',b,60)
   params.append(dict(type=typ,tag=tag,name=b[8:40].split(b'\0')[0].decode(),min=nums[0],max=nums[1],mid=nums[2],default=nums[3],delta=nums[4],flags=flags,title=text(title),unit=text(unit) if unit else '',curve=text(curve) if curve else ''))
  # Supplemental context supplies only this exact requested callback body.
  callback_name='_ZN8Presonus5Panel17FxPresetComponent14presetRecalledERKNS0_15PresetComponentEi'
  supplemental=ROOT/'temp/recovery-work/rolling200-02/next-implementation11/fx-callback-packet02/native-context.json'
  bound=json.loads(supplemental.read_text())['bodies']['native:ed94886022336ee3ad364d28157d7452b90de47b3b793010ff47da726d4658ca']
  cs=tab.get_symbol_by_name(callback_name)[0];sec=e.get_section(cs['st_shndx']);ca=cs['st_value'];cn=cs['st_size'];co=sec['sh_offset']+ca-sec['sh_addr']
  assert (ca,cn,co,digest(blob[co:co+cn]))==(bound['address'],bound['size'],bound['file_offset'],bound['bytes_sha256'])
  callback_range=dict(mangled=callback_name,address=ca,size=cn,file_offset=co,section=sec.name,sha256=digest(blob[co:co+cn]))
  callback_cases=[]
  for receiver in (0x1001000,0x1003000):
   for slot_value in (0,1,0xffffffff,0x80000000,0x7fffffff):
    cu=Uc(UC_ARCH_ARM,UC_MODE_ARM);cu.mem_map(ca&~4095,4096);cu.mem_write(ca,blob[co:co+cn]);cu.mem_map(0x1000000,0x10000);cu.mem_map(0x9000000,0x10000)
    stop=0x100f000;pcs=[];writes=[]
    def callback_code(uc,pc,n,_):
     if pc==stop:uc.emu_stop();return
     assert ca<=pc<ca+cn;pcs.append(pc)
    def callback_write(uc,access,addr,n,val,_):
     assert 0x9000000<=addr and addr+n<=0x9010000
     writes.append([addr,n,val])
    cu.hook_add(UC_HOOK_CODE,callback_code);cu.hook_add(UC_HOOK_MEM_WRITE,callback_write)
    for reg,val in [(UC_ARM_REG_R0,receiver),(UC_ARM_REG_R1,0x1005000),(UC_ARM_REG_R2,slot_value),(UC_ARM_REG_SP,0x9008000),(UC_ARM_REG_LR,stop)]:cu.reg_write(reg,val)
    before=bytes(cu.mem_read(0x1000000,0x10000));cu.emu_start(ca,stop+4,count=20)
    assert cu.reg_read(UC_ARM_REG_PC)==stop and bytes(cu.mem_read(0x1000000,0x10000))==before
    assert pcs==list(range(ca,ca+cn,4)) and cu.reg_read(UC_ARM_REG_R0)==receiver
    callback_cases.append(dict(receiver=receiver,slot_bits=slot_value,executed_pcs=pcs,stack_writes=writes,application_memory_unchanged=True,r0_after=cu.reg_read(UC_ARM_REG_R0),r1_after=cu.reg_read(UC_ARM_REG_R1),r2_after=cu.reg_read(UC_ARM_REG_R2),external_calls=[]))
  cases=[]
  for kind,name in [('base',BASE),('c1',FX.format(1)),('c2',FX.format(2))]:
   for present in (0,1):
    u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x600000)
    for seg in e.iter_segments():
     if seg['p_type']=='PT_LOAD':u.mem_write(seg['p_vaddr'],seg.data())
    obj=0x1000000;front=obj+0x1000;mixer=obj+0x2000;slot=obj+0x3000;string=obj+0x4000;selection=obj+0x5000;vt=obj+0x6000;cast=vt+0x100;reset=vt+0x104;stop=obj+0xf000;stack=0x9000000
    u.mem_map(obj,0x10000);u.mem_map(stack,0x10000)
    def word(a,v):u.mem_write(a,struct.pack('<I',v))
    def read(a):return struct.unpack('<I',u.mem_read(a,4))[0]
    def txt(a):return bytes(u.mem_read(a,100)).split(b'\0',1)[0].decode()
    word(string,vt);word(vt,cast);word(vt+0x5c,reset)
    for off,val in [(0x7000,b'base\0'),(0x7100,b'Display\0'),(0x7200,b'reverbnum\0')]:u.mem_write(obj+off,val)
    trace=[];pcs=[];writes=[];observations={};registered=[]
    def code(uc,pc,n,_):
     r0=uc.reg_read(UC_ARM_REG_R0);r1=uc.reg_read(UC_ARM_REG_R1);r2=uc.reg_read(UC_ARM_REG_R2)
     if pc==stop:uc.emu_stop();return
     ret=None
     if pc==0x119e8c:assert r0==obj;observations['name']=txt(r1);trace.append('component')
     elif pc==0x1debc:assert r0==obj+0x90;observations['display']=txt(r1);u.mem_write(r0,txt(r1).encode()[:31]+b'\0');trace.append('display')
     elif pc in (0x84508,0x56f34):
      expected=obj+(0xb0 if pc==0x84508 else 0xcc);assert r0==expected and r1==0 and read(expected+16)==5;trace.append('delegates' if pc==0x84508 else 'recalls')
     elif pc==0x11ec54:assert r0==obj+0x28 and r1==0x3570a0 and r2==4;trace.append('params')
     elif pc==0x119c4c:
      if r0==obj:assert r1 in (0,2);ret=slot if r1==0 else string;trace.append('tag'+str(r1))
      else:assert r0==front and r1==13;ret=selection if present else 0;trace.append('tag13')
     elif pc==0x110810:observations['formatter']=txt(r0);ret=0x123456;trace.append('formatter')
     elif pc==cast:assert r0==string and r1==1397776754;ret=string;trace.append('string-cast')
     elif pc==0x11df74:assert r0==string;observations['default_text']=txt(r1);trace.append('default')
     elif pc==reset:assert r0==string and r1==0;observations['current_text']=observations['default_text'];trace.append('reset0')
     elif pc==0x11d4f4:assert present and r0==selection and r1==obj+4;registered.append(r1);trace.append('observer')
     elif pc==0x835ec:assert r0==obj and r1==obj+0xc8;trace.append('delegate')
     else:
      assert any(a<=pc<a+n for a,n in targets.values()),hex(pc)
      pcs.append(pc);return
     if ret is not None:uc.reg_write(UC_ARM_REG_R0,ret)
     uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
    def write(uc,access,p,n,val,_):
     if obj<=p<obj+0x100: writes.append([p-obj,n,val])
    u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
    u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_SP,stack+0x8000);u.reg_write(UC_ARM_REG_LR,stop)
    if kind=='base':
     u.reg_write(UC_ARM_REG_R1,obj+0x7000);u.reg_write(UC_ARM_REG_R2,obj+0x7100);u.reg_write(UC_ARM_REG_R3,obj+0x7200);word(stack+0x8000,mixer)
    else:u.reg_write(UC_ARM_REG_R1,front);u.reg_write(UC_ARM_REG_R2,mixer)
    u.emu_start(targets[name][0],stop+4,count=1000);assert u.reg_read(UC_ARM_REG_PC)==stop
    assert read(obj+0xc4)==mixer and read(obj+0x8c)==slot and read(slot+16)==0x123456
    assert read(obj+0xb4)==read(obj+0xb8)==read(obj+0xbc)==0
    assert read(obj+0xc0)==5
    if kind!='base':
     assert read(obj+0xd0)==read(obj+0xd4)==read(obj+0xd8)==read(obj+0xe8)==0
     assert read(obj+0xdc)==5 and read(obj+0xe0)==front and read(obj+0xe4)==(selection if present else 0)
     assert trace[-1]=='delegate' and (not present or trace[-2]=='observer')
    expected='|'.join([observations['name'],observations['display'],observations['formatter'],observations['current_text'],str(present if kind!='base' else 0)])+'\n'
    cases.append(dict(kind=kind,present=present,argv=[kind,str(present)],expected=expected,observations=observations,trace=trace,writes=writes,executed_pcs=pcs,observer_membership=registered))
 return dict(elf_path=str(ELF.relative_to(ROOT)),elf_sha256=SHA,ranges=ranges,callback_range=callback_range,callback_cases=callback_cases,parameter_table=dict(address=0x3570a0,size=336,sha256=digest(table),params=params),cases=cases,limitations='Full byte ranges verified separately; normal constructor instruction paths executed, including authentic base C2. Core calls and membership vector bodies are typed provider boundaries. Native ARM exception unwinding is not executed; host allocation failure/rollback tested independently with actual C++ runtime. No original inheritance/layout/ARM ABI/hardware claim.')
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();pathlib.Path(a.out).write_text(json.dumps(generate(),indent=2)+'\n')
