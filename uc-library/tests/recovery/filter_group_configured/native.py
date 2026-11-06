"""Exact original application instructions; no Core firmware execution."""
import hashlib,itertools,json,pathlib,struct,sys
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ROOT=pathlib.Path(__file__).resolve().parents[4]
BASE=pathlib.Path('uc-library/tests/recovery/filter_group_configured')
PACKET=pathlib.Path('temp/recovery-work/rolling200-02/next-implementation126/prepared126/packets/rolling200_02_filter_group126')
ELF='rootfs/RML16AI_Rack_13731/home/root/mixer';SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
OBJ=0x1000000;PAR=OBJ+0x1000;STACK=0x1100000;SP=STACK+0x8000;STOP=0x1200000

def verified():
 raw=(ROOT/ELF).read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
 j=json.loads((ROOT/PACKET/'native-context.json').read_text());b=j['bodies'][j['roots'][0]]
 with (ROOT/ELF).open('rb') as f:
  elf=ELFFile(f);sec=elf.get_section(b['section_index']);offset=sec['sh_offset']+b['address']-sec['sh_addr'];assert offset==b['file_offset'] and sec.name==b['section']
  body=raw[offset:offset+b['size']];assert hashlib.sha256(body).hexdigest()==b['bytes_sha256'] and len(body)==84
 return {k:b[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']},body

def execute(b,body,kind,tag,first,tail,advertised):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
 for a in [b['address']&~4095,0x119000,0xa000,OBJ,PAR,STACK,STACK+0x7000,STACK+0x8000,STOP]:u.mem_map(a,4096)
 u.mem_write(b['address'],body);u.mem_write(PAR+44,bytes([first,tail,0]));trace=[];writes=[]
 def hook(uc,a,n,user):
  if a==0x119c4c:
   assert uc.reg_read(UC_ARM_REG_R0)==OBJ and uc.reg_read(UC_ARM_REG_R1)==600
   found=bool(kind and tag==600);trace.append(['getParameterByTag',600,int(found)])
   uc.reg_write(UC_ARM_REG_R0,PAR if found else 0);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
  if a==0xacf4:
   args=[uc.reg_read(r) for r in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]]
   assert args==[PAR,4305512,4305388,0],args
   trace.append(['dynamic_cast_Parameter_StringParam',int(kind==2)])
   uc.reg_write(UC_ARM_REG_R0,PAR if kind==2 else 0);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
  assert b['address']<=a<a+n<=b['address']+b['size'],hex(a)
 def write(uc,access,a,n,v,user):
  assert SP-64<=a<a+n<=SP,(hex(a),n);writes.append([a-SP,n,v])
 u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
 for reg,val in [(UC_ARM_REG_R0,OBJ),(UC_ARM_REG_SP,SP),(UC_ARM_REG_LR,STOP)]:u.reg_write(reg,val)
 u.emu_start(b['address'],STOP,count=100);assert u.reg_read(UC_ARM_REG_PC)==STOP
 assert bytes(u.mem_read(PAR+44,3))==bytes([first,tail,0])
 return dict(input=[kind,tag,first,tail,advertised],result=u.reg_read(UC_ARM_REG_R0),trace=trace,stack_writes=writes)

def generate():
 b,body=verified();cases=[]
 for kind,tag,first,tail,advertised in itertools.product(range(3),[599,600,601],range(256),[0,65],range(2)):
  cases.append(execute(b,body,kind,tag,first,tail,advertised))
 return dict(elf=ELF,elf_sha256=SHA,ranges=[b],cases=cases,boundaries='Exact 84-byte app range including literal pool. Original Core getParameterByTag and ABI dynamic_cast are intercepted using explicit fixture lookup/runtime-class state, with exact argument checks. No Core firmware executes. Original byte+44 initialized independently; advertised descriptor metadata and tail sentinel do not affect intercepted type. All writes bounded to stack; observed byte unchanged. Provider mapping of this byte to getText is intentional source adaptation, not recovered ARM layout.')
if __name__=='__main__':
 j=generate();p=ROOT/BASE/'fixtures.json'
 if '--generate' in sys.argv:p.write_text(json.dumps(j,indent=2)+'\n')
 else:assert j==json.loads(p.read_text())
 print(len(j['cases']),'original ARM executions, exact range verified')
