"""Execute original app constructor chain only; external Core providers are opaque.
Provider boundary interception records calls, NOT native Core behavior/cleanup.
Actual pinned provider construction/cleanup is tested by the C++ lifecycle mode.
"""
import json,pathlib,hashlib,struct,argparse
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
elf=pathlib.Path('rootfs/RML16AI_Rack_13731/home/root/mixer').read_bytes();assert hashlib.sha256(elf).hexdigest()=='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
providers={0x119e8c:'Core::Portable::Component::C2',0x121dbc:'Core::Portable::AttributeAllocator::getDefault',0x121a68:'Core::Portable::Attributes::C1'};apps={0x82ab4:'DspComponent::C1',0x82a48:'LinkableComponent::C2',0x829a0:'TargetedComponent::C2',0xf6160:'UC::ServerComponent::C2'};rows=[]
for name in ['', 'fixture','long-component-name','x'*31,'y'*32,'z'*65]:
 for controller in [0,0x1001000]:
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x500000);u.mem_write(0x8000,elf[:0x500000]);u.mem_map(0x1000000,0x10000);u.mem_map(0x2000000,0x10000);obj=0x1000000;u.mem_write(obj,b'\xa5'*512);u.mem_write(0x1002000,name.encode()+b'\0');trace=[];writes=[];calls=[]
  u.reg_write(UC_ARM_REG_SP,0x2008000);u.reg_write(UC_ARM_REG_LR,0x100f000);u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_R1,0x1002000);u.reg_write(UC_ARM_REG_R2,controller)
  def hook(uc,address,size,data):
   if address in apps:trace.append(apps[address])
   if address in providers:
    calls.append({'provider':providers[address],'r0':uc.reg_read(UC_ARM_REG_R0),'r1':uc.reg_read(UC_ARM_REG_R1),'name':bytes(uc.mem_read(uc.reg_read(UC_ARM_REG_R1),len(name)+1)).split(b'\0')[0].decode() if address==0x119e8c else None});trace.append(providers[address]);uc.reg_write(UC_ARM_REG_R0,0x1003000 if address==0x121dbc else uc.reg_read(UC_ARM_REG_R0));uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  def write(uc,access,address,size,value,data):
   if obj<=address<obj+512:writes.append({'offset':address-obj,'size':size,'value':value})
  u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write);u.emu_start(0x82ab4,0x100f000,count=10000)
  read=lambda off:struct.unpack('<I',u.mem_read(obj+off,4))[0]
  rows.append({'name':name,'controller':controller,'trace':trace,'provider_calls':calls,'app_writes':writes,'state':{'serverFlag':u.mem_read(obj+0x84,1)[0],'baseFlag':u.mem_read(obj+0x28,1)[0],'targetedFlag':u.mem_read(obj+0x85,1)[0],'slave':u.mem_read(obj+0x8c,1)[0],'enabled':u.mem_read(obj+0x8d,1)[0],'partner':read(0x88),'controller':read(0xb0),'readoutCount':read(0xb8),'readoutInline':read(0xb4)==obj+0xbc}})
pathlib.Path(a.out).write_text(json.dumps(rows,indent=2));print('12 original C1 app-chain executions; Core implementation excluded')
