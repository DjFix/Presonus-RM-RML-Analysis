"""Original ARM only, private memory, explicit provider boundaries and strict guards."""
import hashlib,json,pathlib,struct
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
from elftools.elf.elffile import ELFFile
ROOT=pathlib.Path(__file__).resolve().parents[5]
PACKETS='temp/recovery-work/rolling200-02/implementation-plan01/packets-current-eq-band03-01/packets'
ELF='rootfs/CS18_v13840/home/root/surface'
SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
OBJ=0x400000; BANDS=0x410000; CURVES=0x420000; STACK=0x500000; SP=STACK+0x8000; STOP=0x600000
REMOVE=0x11e2e0; ADD=0x11f4f0

def verified():
 raw=(ROOT/ELF).read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
 bodies=[]
 with (ROOT/ELF).open('rb') as f:
  elf=ELFFile(f)
  for n in ['01','02','03']:
   j=json.loads((ROOT/PACKETS/f'rolling200_02_eq_band_{n}/native-context.json').read_text()); b=j['bodies'][j['roots'][0]]
   sec=elf.get_section(b['section_index']); offset=sec['sh_offset']+b['address']-sec['sh_addr']
   assert sec.name==b['section'] and offset==b['file_offset']
   code=raw[offset:offset+b['size']];assert hashlib.sha256(code).hexdigest()==b['bytes_sha256']
   bodies.append(({k:b[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']},code))
 return bodies

def execute(bodies,mode,nonnull,index,count,old,new):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
 for page in sorted({b['address']&~4095 for b,_ in bodies}|{REMOVE&~4095,ADD&~4095}):u.mem_map(page,4096)
 for b,code in bodies:u.mem_write(b['address'],code)
 for address in [OBJ,BANDS,CURVES,STACK,STOP]:u.mem_map(address,65536 if address==STACK else 4096)
 def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def words(a,n):return list(struct.unpack('<'+'I'*n,u.mem_read(a,4*n)))
 def pointer(v):return OBJ+0x1000+4*v if v else 0
 def decode(v):return (v-OBJ-0x1000)//4 if v else 0
 for i in range(count):
  for s,v in enumerate(old):w(BANDS+24*i+4*s,pointer(v))
  u.mem_write(CURVES+40*i+20,b'\x07')
 w(OBJ+0x70,count);w(OBJ+0x78,BANDS);w(OBJ+0xf0,CURVES)
 trace=[];writes=[]
 def hook(uc,a,size,user):
  if a in [REMOVE,ADD]:
   row=[int(a==ADD),decode(uc.reg_read(UC_ARM_REG_R0)),int(uc.reg_read(UC_ARM_REG_R1)!=0)]
   assert uc.reg_read(UC_ARM_REG_R1)==(OBJ+0x44 if nonnull or mode==2 else 0)
   if 0<=index<count:row += [decode(v) for v in words(BANDS+24*index,6)]+[uc.mem_read(CURVES+40*index+20,1)[0]]
   trace.append(row);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
  assert any(b['address']<=a<a+size<=b['address']+b['size'] for b,_ in bodies),(hex(a),size)
 def write(uc,access,a,size,value,user):
  assert STACK<=a<a+size<=SP or (mode==2 and 0<=index<count and (BANDS+24*index<=a<a+size<=BANDS+24*(index+1) or (a==CURVES+40*index+20 and size==1))), (hex(a),size)
  if not STACK<=a<SP:writes.append([a,value,size])
 u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
 u.reg_write(UC_ARM_REG_SP,SP);u.reg_write(UC_ARM_REG_LR,STOP)
 u.reg_write(UC_ARM_REG_R0,OBJ if mode==2 else BANDS)
 u.reg_write(UC_ARM_REG_R1,index&0xffffffff if mode==2 else (OBJ if nonnull else 0))
 if mode==2:
  u.reg_write(UC_ARM_REG_R2,pointer(new[0]));u.reg_write(UC_ARM_REG_R3,pointer(new[1]))
  for i,v in enumerate(new[2:]):w(SP+4*i,pointer(v))
 start=bodies[mode][0]['address'];u.emu_start(start,STOP,count=5000);assert u.reg_read(UC_ARM_REG_PC)==STOP
 final=[[decode(v) for v in words(BANDS+24*i,6)] for i in range(count)]
 dirty=[u.mem_read(CURVES+40*i+20,1)[0] for i in range(count)]
 return dict(input=[mode,nonnull,index,count]+old+new,trace=trace,final=final,dirty=dirty,writes=writes)

def generate():
 bodies=verified();cases=[]
 patterns=[[0]*6,[1,2,3,4,5,6],[1]*6,[1,0,2,0,3,0],[0,1,0,2,0,3]]+[[int(i==j)*(j+1) for i in range(6)] for j in range(6)]
 for mode in [0,1]:
  for nonnull in [0,1]:
   for old in patterns:cases.append(execute(bodies,mode,nonnull,0,1,old,[0]*6))
 for count in [0,1,3]:
  for index in sorted(set([-1,0,count-1,count])):
   for old in patterns[:5]:
    for new in [[0]*6,[7,8,9,10,11,12],[1]*6,old]:cases.append(execute(bodies,2,1,index,count,old,new))
 return {'ranges':[b for b,_ in bodies],'cases':cases,'boundary':'Real original ARM bodies; Parameter add/remove modeled and traced, Core binary execution excluded. Stable count/pointers during synchronous provider calls; writes strictly guarded.'}
if __name__=='__main__':
 import sys
 out=ROOT/'evidence/recovery/2026-11-05/rolling200-02/eq-band/native.json'
 j=generate()
 if '--generate' in sys.argv:out.write_text(json.dumps(j,indent=2)+'\n')
 else:assert j==json.loads(out.read_text())
 print(len(j['cases']),'independent original ARM cases; exact ranges and strict PC/write guards')
