"""Restricted original ARM targets; synthetic memory and named provider boundaries.
No Core body, hardware, syscall or firmware lifecycle is executed.
"""
import hashlib,json,pathlib,struct
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ROOT=pathlib.Path(__file__).resolve().parents[5]
PACKETS=pathlib.Path('temp/recovery-work/rolling200-02/next-implementation10/prepared-midi10/packets')
OUT=pathlib.Path('evidence/recovery/2026-11-05/rolling200-02/midi-dispatch/native.json')
ELF='rootfs/CS18_v13840/home/root/surface'
SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
O=0x400000; SP=0x508000; STOP=0x600000
GET=0x600100; RELEASE=0x600104; BUTTON=0x600108; ENCODER=0x60010c; SCRUB=0x600110; ORIGINAL=0x600114; VALUE=0x600118

def verified():
 raw=(ROOT/ELF).read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
 bodies=[]
 with (ROOT/ELF).open('rb') as f:
  elf=ELFFile(f)
  for n in range(1,5):
   j=json.loads((ROOT/PACKETS/f'rolling200_02_midi_dispatch10_{n:02}/native-context.json').read_text());b=j['bodies'][j['roots'][0]]
   sec=elf.get_section(b['section_index']);offset=sec['sh_offset']+b['address']-sec['sh_addr'];assert offset==b['file_offset'] and sec.name==b['section']
   code=raw[offset:offset+b['size']];assert hashlib.sha256(code).hexdigest()==b['bytes_sha256'];bodies.append(({k:b[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']},code))
  supplemental=ROOT/'temp/recovery-work/rolling200-02/next-implementation11'
  for folder in ['expand-midi-fcmpeq11','midi-floatflags-packet','expand-midi-cmpsf11']:
   j=json.loads((supplemental/folder/'native-context.json').read_text())
   for key,b in j['bodies'].items():
    node=j['nodes'][key]
    if node['elf']!=SHA:continue
    sec=elf.get_section(b['section_index']);offset=sec['sh_offset']+b['address']-sec['sh_addr']
    assert offset==b['file_offset'] and sec.name==b['section']
    code=raw[offset:offset+b['size']];assert hashlib.sha256(code).hexdigest()==b['bytes_sha256']
    record={k:b[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']}
    record.update(mangled=node['metadata']['mangled'],elf_sha256=SHA,scope='compiler support observation only; no reconstruction/readiness credit')
    bodies.append((record,code))
 return bodies

def signed(n):return n if n<2**31 else n-2**32

def execute(bodies,inp):
 method,controller,index,delta,acc,present,bits,flag,pressed,original,incoming=inp
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
 external=[0xbd63c,0xbd5ec,0x15cc0,0x11acf0,0x187780,0x1864b8]
 for page in sorted({b['address']&~4095 for b,_ in bodies}|{a&~4095 for a in external}):u.mem_map(page,4096)
 for b,code in bodies:u.mem_write(b['address'],code)
 for base,size in [(O,0x10000),(0x500000,0x10000),(STOP,0x1000)]:u.mem_map(base,size)
 def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def r(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 w(O+8,controller);w(O+0xe8,O+0x1000);w(O+0x1000,O+0x2000);w(O+0x100c,O+0x2100)
 for i in range(17):w(O+0xa0+4*i,acc)
 for i in [0,1]:
  w(O+0x2000+i*0x100,O+0x3000);w(O+0x4000+i*0x100,O+0x3100)
 w(O+0x302c,GET)
 for off,a in [(0x2c,RELEASE),(0x18,BUTTON),(0x24,ENCODER),(0x28,SCRUB)]:w(O+0x3100+off,a)
 w(O+0x5000,O+0x5200);w(O+0x520c,ORIGINAL);w(O+0x5244,VALUE)
 w(O+0x510c,O+0x5300);w(O+0x5304,index);w(O+0x533c,flag)
 trace=[];writes=[];helper_returns=[]
 def ret(value=None):
  if value is not None:u.reg_write(UC_ARM_REG_R0,value&0xffffffff)
  u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def hook(uc,a,size,user):
  r0=uc.reg_read(UC_ARM_REG_R0);r1=uc.reg_read(UC_ARM_REG_R1);r2=uc.reg_read(UC_ARM_REG_R2)
  if a==0xbd500:helper_returns.append(r0)
  if a==GET:
   which=int(r0==O+0x2100);assert r0 in [O+0x2000,O+0x2100];trace.append(f'getModel {which}');ret(O+0x4000+which*0x100)
  elif a in [RELEASE,BUTTON,ENCODER,SCRUB]:
   which=int(r0==O+0x4100);assert r0 in [O+0x4000,O+0x4100]
   name={RELEASE:'release',BUTTON:'button',ENCODER:'encoder',SCRUB:'scrub'}[a]
   args='' if a==RELEASE else ' '+str(signed(r1)) if a==SCRUB else f' {signed(r1)} {signed(r2)}'
   trace.append(f'{name} {which}'+args);ret()
  elif a==0xbd63c:trace.append(f'enable {r1}');ret()
  elif a==0xbd5ec:trace.append('colors');ret()
  elif a==0x15cc0:trace.append(f'parameter {present}');ret(O+0x5000 if present else 0)
  elif a==ORIGINAL:trace.append(f'original {original}');ret(O+0x5100 if original else 0)
  elif a==0x11acf0:assert r1==1;trace.append(f'lookup {present}');ret(O+0x5000 if present else 0)
  elif a==VALUE:trace.append(f'value {bits}');ret(bits)
  elif a==0x1864b8:
   v=signed(r0);ret(abs(v)//r1*(-1 if v<0 else 1))
  else:assert any(b['address']<=a and a+size<=b['address']+b['size'] for b,_ in bodies),hex(a)
 def write(uc,access,a,size,value,user):
  assert 0x500000<=a and a+size<=SP or (a==O+8 and size==4) or (O+0xa0<=a and a+size<=O+0xe4 and size==4),(hex(a),size)
  if a<0x500000:writes.append([a-O,size,value])
 u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
 u.reg_write(UC_ARM_REG_SP,SP);u.reg_write(UC_ARM_REG_LR,STOP);u.reg_write(UC_ARM_REG_R0,O);u.reg_write(UC_ARM_REG_R1,incoming if method==2 else O+0x7000);u.reg_write(UC_ARM_REG_R2,index&0xffffffff);u.reg_write(UC_ARM_REG_R3,delta&0xffffffff)
 if method==3:w(SP,pressed);w(SP+4,O+0x6000)
 else:w(SP,0)
 u.emu_start(bodies[method-1][0]['address'],STOP,count=3000);assert u.reg_read(UC_ARM_REG_PC)==STOP
 return {'input':inp,'trace':trace,'accumulation':[r(O+0xa0+4*i) for i in range(17)],'controller':r(O+8),'writes':writes,'float_helper_returns':helper_returns}

def main():
 bodies=verified();cases=[]
 def add(*args):cases.append(execute(bodies,list(args)))
 for method in [1,2]:
  for ctrl in [0,1]:
   for incoming in [0,1]:add(method,ctrl,0,0,0xffffffff,0,0,0,0,0,incoming)
 for ctrl in [0,1]:
  for present in [0,1]:
   for orig in [0,1]:
    for flag in [0,64,128,192]:
     for pressed in [0,1]:add(3,ctrl,0x1234,0,17,present,0,flag,pressed,orig,0)
 for index in [-1,0,7,8,15,16,17,-2147483648]:
  for present,bits in [(0,0),(1,0),(1,0x80000000),(1,0x3f800000),(1,0xbf800000),(1,0x7f800000),(1,0xff800000),(1,0x7fc00000),(1,0x7f800001)]:
   for delta,acc in [(0,0),(4,0),(5,0),(-5,0),(15,0),(-16,0),(1,0x7fffffff),(-1,0x80000000),(2147483647,2147483647),(-2147483648,0),(1,0xffffffff)]:add(4,1,index,delta,acc,present,bits,0,0,0,0)
 add(4,0,0,100,7,1,0,0,0,0,0)
 (ROOT/OUT).write_text(json.dumps({'elf_sha256':SHA,'ranges':[b for b,_ in bodies],'cases':cases},indent=2)+'\n');print(len(cases),'restricted original ARM cases, four target ranges plus separately verified float helper aliases')
if __name__=='__main__':main()
