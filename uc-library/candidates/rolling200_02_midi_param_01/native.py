"""Execute only the original application caller; Core is a named source-provider boundary."""
import hashlib,json,struct,subprocess,functools,sys,io
from elftools.elf.elffile import ELFFile
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ELF=Path('rootfs/CS18_v13840/home/root/surface');data=ELF.read_bytes();SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
assert hashlib.sha256(data).hexdigest()==SHA
ADDRESS=0xbe35c;SIZE=372;OFFSET=0xb635c;body=data[OFFSET:OFFSET+SIZE];RANGE='42b27bb19ef06e9b354ff12b593348fbde42569526adc8b07328099bd26d39c8'
assert hashlib.sha256(body).hexdigest()==RANGE
elf=ELFFile(io.BytesIO(data));section=elf.get_section(12)
assert section.name=='.text' and section['sh_type']=='SHT_PROGBITS'
assert section['sh_offset']+ADDRESS-section['sh_addr']==OFFSET
assert ADDRESS+SIZE<=section['sh_addr']+section['sh_size']
symbols=[s for s in elf.get_section_by_name('.symtab').iter_symbols() if s.name=='_ZN8Presonus7Surface16MidiMixerHandler12paramChangedEPN4Core8Portable9ParameterEi']
assert len(symbols)==1 and symbols[0]['st_value']==ADDRESS and symbols[0]['st_size']==SIZE and symbols[0]['st_shndx']==12
EXE=sys.argv[1] if len(sys.argv)>1 else 'temp/recovery-work/midi-param01/replay'
@functools.lru_cache(None)
def insert(text,index,literal):
 return bytes.fromhex(subprocess.check_output([EXE,'insert',text.hex(),str(index),literal],text=True).strip())
def run(v):
 tag,cast,mode,first,second,text,mutation=v;text=bytes.fromhex(text)[:255]
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
 u.mem_map(0xbe000,0x1000);u.mem_write(ADDRESS,body)
 # Explicit source-provider entry traps, no original Core instructions mapped.
 boundaries=[0xae58,0x11acf0,0x187780,0xaffc,0x9bc08,0xbd934,0x10000,0x10100,0x10200]
 for page in sorted({x&~4095 for x in boundaries}):u.mem_map(page,4096)
 u.mem_map(0x400000,0x10000);u.mem_map(0x500000,0x10000)
 u.mem_map(0x1f2000,0x1000);u.mem_map(0x200000,0x1000);u.mem_map(0x207000,0x1000)
 for a,s in [(0x1f214c,b':\0'),(0x200d80,b'.\0'),(0x207ffc,b"'\0")]:u.mem_write(a,s)
 def word(a,v):u.mem_write(a,struct.pack('<I',v))
 self_=0x500000;param=0x501000;info=0x502000;number=0x503000;output=0x504000;vt=0x505000
 word(param+12,info);word(info+4,tag&0xffffffff);u.mem_write(param+44,text+b'\0'+b'\0'*(255-len(text)))
 word(number,vt);word(output,vt);word(vt+68,0x10100);word(vt+116,0x10200)
 trace=[];calls=[];writes=[];reads=0;present=bool(mode)
 def cstr(a):
  out=b''
  for i in range(256):
   b=bytes(u.mem_read(a+i,1))
   if b==b'\0':return out
   out+=b
  raise AssertionError('unterminated provider string')
 def reg(r):return u.reg_read(r)
 def hook(uc,pc,size,_):
  nonlocal reads,present
  if ADDRESS<=pc<0xbe4b8:return
  assert pc in boundaries,hex(pc)
  r0,r1,r2,r3=[reg(x) for x in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
  calls.append([hex(pc),r0,r1,r2,r3])
  if pc==0xae58:
   assert (r0,r1,r2,r3)==(param,0x2053b0,0x205334,0)
   uc.reg_write(UC_ARM_REG_R0,param if cast else 0)
  elif pc==0x11acf0:
   assert r0==self_+12 and r1 in (5,2)
   p=output if r1==2 else (number if present else 0)
   trace.append(f'lookup {r1} {int(bool(p))}');uc.reg_write(UC_ARM_REG_R0,p)
  elif pc==0x10100:
   assert r0==number
   bits=first if reads==0 else second if mutation==1 else first
   reads+=1;trace.append(f'value {bits}');uc.reg_write(UC_ARM_REG_R0,bits)
   if reads==1 and mutation==2:present=False
  elif pc==0x187780:
   assert r1==0
   # IEEE equality: +0 and -0 equal zero; NaNs are unequal.
   uc.reg_write(UC_ARM_REG_R0,int(struct.unpack('<f',struct.pack('<I',r0))[0]==0.0))
  elif pc==0xaffc:
   assert r1==param+44 and r2==256 and 0x400000<=r0<0x410000-256
   uc.mem_write(r0,bytes(uc.mem_read(r1,r2)))
  elif pc==0x9bc08:
   assert r1 in (3,6,9) and r2 in (0x1f214c,0x200d80,0x207ffc)
   s=insert(cstr(r0),r1,cstr(r2).decode());uc.mem_write(r0,s+b'\0');uc.reg_write(UC_ARM_REG_R0,r0)
  elif pc==0x10200:
   assert r0==output and r2==0
   trace.append('output 0 '+cstr(r1).hex())
  elif pc==0xbd934:
   assert r0==self_;trace.append('record-helper')
  elif pc==0x10000:return
  uc.reg_write(UC_ARM_REG_PC,reg(UC_ARM_REG_LR))
 def write(uc,access,address,size,value,_):
  assert 0x400000<=address and address+size<=0x410000,(hex(address),size)
  writes.append([address,size,value])
 u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
 u.reg_write(UC_ARM_REG_R0,self_);u.reg_write(UC_ARM_REG_R1,param);u.reg_write(UC_ARM_REG_R2,0xffffffef);u.reg_write(UC_ARM_REG_SP,0x40f000);u.reg_write(UC_ARM_REG_LR,0x10000)
 u.emu_start(ADDRESS,0x10000,count=1000);assert reg(UC_ARM_REG_PC)==0x10000
 return dict(input=v,trace=trace,boundary_calls=calls,original_instruction_writes=writes)
cases=[]
texts=[b'',b'0',b'01',b'012',b'0123',b'01234',b'012345',b'01234567',b'012345678',b'0123456789']+[b'x'*n for n in (252,253,254,255,300)]
# First/second modes cover null, stable ±zero/nonzero/NaN, replacement and removal.
states=[(0,0,0,0)]+[(1,x,x,0) for x in (0,0x80000000,0x3f800000,0xbf800000,0x7fc00000)]+[(1,x,y,1) for x in (0,0x80000000,0x3f800000,0x7fc00000) for y in (0,0x80000000,0x3f800000,0x7fc00000)]+[(1,x,0,2) for x in (0,0x3f800000)]
for tag in (4,5,0xa007):
 for text in texts:
  for mode,first,second,mutation in states:cases.append(run([tag,1,mode,first,second,text.hex(),mutation]))
for tag in (0,1,2,3,6,-1,0xa006,0xa008,4,5,0xa007):
 for cast in (0,1):cases.append(run([tag,cast,1,0x3f800000,0,'30313233343536373839',0]))
print(json.dumps(dict(elf_sha256=SHA,address=ADDRESS,size=SIZE,section='.text',file_offset=OFFSET,range_sha256=RANGE,oracle='Original caller only; pinned CCL CString256 insert source provider; named getValue, RTTI, lookup, equality, output and helper boundaries',cases=cases),indent=2))
