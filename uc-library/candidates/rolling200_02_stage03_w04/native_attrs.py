from pathlib import Path
import json,hashlib,struct,itertools,ctypes
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
R=Path.cwd();A=Path(__file__).resolve().parent;O=R/'evidence/recovery/2026-11-05/rolling200-02/stage03-w04/native-attrs';O.mkdir(parents=True,exist_ok=True)
elf=R/'rootfs/CS18_v13840/home/root/surface';data=elf.read_bytes();assert hashlib.sha256(data).hexdigest()=='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
row=dict(address=0x65fac,size=632,file_offset=0x5dfac,section='.text',elf_sha256=hashlib.sha256(data).hexdigest());raw=data[row['file_offset']:row['file_offset']+row['size']];assert hashlib.sha256(raw).hexdigest()=='333c44ffeb006cbcbd77a092edf7c6885519f28d71514b956daceda4c611f5ae'
# Decode exact original EnumInfo row and pointee, not a generated option table.
from elftools.elf.elffile import ELFFile
with elf.open('rb') as f:
 e=ELFFile(f)
 def native(addr,n):
  sec=next(x for x in e.iter_sections() if x['sh_addr']<=addr and addr+n<=x['sh_addr']+x['sh_size']);return data[sec['sh_offset']+addr-sec['sh_addr']:sec['sh_offset']+addr-sec['sh_addr']+n]
 table=native(0x19b248,16);name,value,term,_=struct.unpack('<IIII',table);assert value==0x400000 and term==0;assert native(name,8)==b'reverse\0'
u=Uc(UC_ARCH_ARM,UC_MODE_ARM);obj=0x300000;attrs=obj+0x300;string=0x310000;buffer=0x320000;heap=0x330000;stack=0x400000;stop=0x500000
for p,n in [(0x65000,8192),(0x69000,4096),(obj,4096),(string,0x30000),(stack,0x20000),(stop,4096),(0x10f000,4096),(0x124000,4096),(0xa000,0x2000),(0x187000,4096),(0x19b000,4096),(0x1f2000,4096)]:u.mem_map(p,n)
u.mem_write(row['address'],raw);u.mem_write(0x19b160,b',\0');u.mem_write(0x19b164,b'%f\0');libc=ctypes.CDLL(None);libm=ctypes.CDLL('libm.so.6');sourcepow=libm.powf;sourcepow.argtypes=[ctypes.c_float,ctypes.c_float];sourcepow.restype=ctypes.c_float;mathmeta={'provider':'actual host libm.so.6 powf capture; not original ARM libm execution'}
f32=lambda f:struct.unpack('<f',struct.pack('<f',f))[0];fb=lambda f:struct.unpack('<I',struct.pack('<f',f))[0]
def put(p,v):u.mem_write(p,struct.pack('<I',v&0xffffffff))
def get(p):return int.from_bytes(u.mem_read(p,4),'little')
def cstr(p):
 out=bytearray()
 for i in range(20000):
  x=bytes(u.mem_read(p+i,1))
  if x==b'\0':return bytes(out)
  out.extend(x)
 raise AssertionError('unterminated')
trace=[];state={};cursor=0;resize_attempt=0
scanned=[]
def scan(token):
 v=ctypes.c_float(0);rc=libc.sscanf(ctypes.c_char_p(token),ctypes.c_char_p(b'%f'),ctypes.byref(v));return v.value,rc

def hook(uc,pc,size,_):
 global cursor,resize_attempt
 if pc==stop:uc.emu_stop();return
 r0=uc.reg_read(UC_ARM_REG_R0);r1=uc.reg_read(UC_ARM_REG_R1);r2=uc.reg_read(UC_ARM_REG_R2);result=0
 if pc==0x65dec:assert r0==obj and r1==attrs;trace.append(['Pot::setAttributes']);put(obj+0x40,state['base_options'])
 elif pc==0x10f83c:assert r0==attrs and r1==0x19b248 and r2==0x20ee8c;trace.append(['getOptions']);result=state['parsed']
 elif pc==0x124200:assert r0==attrs and r1==0x19b158;trace.append(['getString']);result=string if state['text'] is not None else 0
 elif pc==0x69e64:
  assert r0==obj+0x70;trace.append(['CoreVector::resize',r1]);result=1
  if r1==0:put(obj+0x74,0);put(obj+0x78,0);put(obj+0x7c,0)
  else:
   resize_attempt+=1
   if resize_attempt==state['fail_growth']:result=0
   else:put(obj+0x74,buffer);put(obj+0x7c,r1)
 elif pc==0xb02c:result=len(cstr(r0));trace.append(['strlen',result])
 elif pc==0xb170:
  data=cstr(r1)[:r2];u.mem_write(r0,data+b'\0'*max(0,r2-len(data)));result=r0;trace.append(['strncpy',r2])
 elif pc==0xac60:assert r0<=20000;result=heap;trace.append(['new[]',r0])
 elif pc==0xad38:u.mem_write(r0,cstr(r1)+b'\0');result=r0;trace.append(['strcpy',len(cstr(r1))])
 elif pc==0xab28:
  assert cstr(r1)==b','
  if r0:cursor=r0
  while bytes(u.mem_read(cursor,1))==b',':cursor+=1
  if bytes(u.mem_read(cursor,1))!=b'\0':
   result=cursor
   while bytes(u.mem_read(cursor,1)) not in [b',',b'\0']:cursor+=1
   if bytes(u.mem_read(cursor,1))==b',':u.mem_write(cursor,b'\0');cursor+=1
  trace.append(['strtok',cstr(result).decode() if result else None])
 elif pc==0xb164:
  assert cstr(r1)==b'%f';value,rc=scan(cstr(r0));put(r2,fb(value));result=rc&0xffffffff;trace.append(['sscanf',cstr(r0).decode(),fb(value),rc])
 elif pc==0x187798:result=int(struct.unpack('<f',struct.pack('<I',r0))[0]<struct.unpack('<f',struct.pack('<I',r1))[0])
 elif pc==0x1873f0:result=fb(f32(struct.unpack('<f',struct.pack('<I',r0))[0]*struct.unpack('<f',struct.pack('<I',r1))[0]))
 elif pc==0xaff0:
  left=struct.unpack('<f',struct.pack('<I',r0))[0];right=struct.unpack('<f',struct.pack('<I',r1))[0];result=fb(sourcepow(left,right));trace.append(['powf',r0,r1,result])
 elif pc==0x18714c:result=fb(f32(struct.unpack('<f',struct.pack('<I',r0))[0]-struct.unpack('<f',struct.pack('<I',r1))[0]))
 elif pc==0xaec4:assert r0==heap;trace.append(['delete[]'])
 else:assert row['address']<=pc<row['address']+row['size'],hex(pc);return
 uc.reg_write(UC_ARM_REG_R0,result);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
u.hook_add(UC_HOOK_CODE,hook);records=[]
texts=[None,'',',,,','0','-6,-12,-24',' -144,-144.0001,-200,0,6','bad,1x,, -6','nan,inf,-inf','1,','  ,2','-6'+(' '*4092),'-6'+(' '*4093),'-6'+(' '*4094)]
for text,base,parsed,fail in itertools.product(texts,[0,0x400000],[0,0x400000],[0,2]):
 state=dict(text=text,base_options=base,parsed=parsed,fail_growth=fail);trace=[];cursor=0;resize_attempt=0;put(obj+0x74,buffer);put(obj+0x78,2);put(obj+0x7c,2);put(buffer,fb(.2));put(buffer+4,fb(.4))
 if text is not None:u.mem_write(string,text.encode()+b'\0')
 u.reg_write(UC_ARM_REG_CPSR,0x10);u.reg_write(UC_ARM_REG_SP,stack+0x1ff00);u.reg_write(UC_ARM_REG_LR,stop);u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_R1,attrs);u.emu_start(row['address'],stop,count=200000);assert u.reg_read(UC_ARM_REG_PC)==stop;assert get(obj+0x40)==(base|parsed)
 count=get(obj+0x78);actual=[get(get(obj+0x74)+i*4) for i in range(count)]
 assert any(x[0]=='new[]' for x in trace)==(text is not None and len(text)>=4096);records.append(dict(text=text,base=base,parsed=parsed,failed_growth=fail,threshold_bits=actual,trace=trace))
(O/'cases.json').write_text(json.dumps(records,indent=2)+'\n');proof=dict(passed=True,cases=len(records),original=row,original_Core_libc_math_bodies_executed=False,host_libm_boundary=mathmeta,sourceprovided_capture='CoreVector resize contract, tokenizer/libc and numeric/existingpinnedsourcePowf boundaries captured beforeexecution; originalARM libm implementation NOT validated',domains='Successfultokenizerallocation<=4097bytes, validstring/vectorstorage; zero/errorprefix/NaN/Inf tokens; injected2ndgrowthfailure dropsitemandcontinues. No exceptions/localechanges/globalstrtokconcurrency proof.');(O/'validation.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'cases':len(records)}))
