"""Execute original ARM targets; app/provider boundaries are explicit scripted captures.
No reconstructed C++ is consulted. ColorMapping and panel implementations are excluded.
"""
import pathlib,json,hashlib,struct,sys
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
ELF_SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
ADDRESSES=[0x764fc,0x75fa0,0x75a78,0x76438,0x75f44,0x763b8,0x76338,0x75e48,0x76c6c,0x766b0]
def observe(path,n,v):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x400000)
 with open(path,'rb') as f:
  for seg in ELFFile(f).iter_segments():
   if seg['p_type']=='PT_LOAD':u.mem_write(seg['p_vaddr'],seg.data())
 u.mem_map(0x1000000,0x400000)
 obj=0x1000000;item=0x1100000;control=0x1120000;alias=0x1130000;pages=0x1140000;page1=0x1110000;page2=0x1111000;vt=0x1150000;stop=0x13ff000
 trace=[]; stopped=[False]
 def w(a,x):u.mem_write(a,struct.pack('<I',x))
 def r(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 def put(a,s):u.mem_write(a,s.encode()+b'\0');return a
 def string(a):
  if not a:return 'NULL'
  b=bytearray()
  while True:
   c=bytes(u.mem_read(a+len(b),1))
   if c==b'\0':return b.decode()
   b.extend(c)
 def reg(i):return u.reg_read([UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3][i])
 def ret(value=0):u.reg_write(UC_ARM_REG_R0,value);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 name=put(0x1160000,'hit' if v else 'miss');mode=put(0x1161000,'mode');color=put(0x1162000,'default' if n==9 and v==3 else 'abcdefghijklmnopqrstuvwxyz0123456789' if n==10 and v==3 else 'red');fast=put(0x1163000,'fast');blue=put(item+40,'blue');one=put(0x1164000,'one');two=put(0x1165000,'two');absent=put(0x1166000,'absent')
 w(item,control if v>=2 else 0);w(control,vt);w(alias,vt+128);w(page1,vt+64);w(page2,vt+64)
 w(vt,0x13fe008);w(vt+16,0x13fe004);w(vt+24,0x13fe010);w(vt+28,0x13fe014);w(vt+64,0x13fe000);w(vt+128,0x13fe00c)
 w(control+12,alias if v==3 else 0);w(control+16,alias if v==3 else 0)
 count=(0 if v==0 else 127 if v==1 else 128) if n==3 else (0 if v==0 else 1 if v==1 else 2) if n==8 else 0
 w(obj+73740,pages);w(obj+73744,count)
 for i in range(count):w(pages+i*4,page1 if n==3 or i==0 else page2)
 for k,val in [(UC_ARM_REG_SP,0x1300000),(UC_ARM_REG_LR,stop),(UC_ARM_REG_R0,obj),(UC_ARM_REG_R1,name),(UC_ARM_REG_R2,0),(UC_ARM_REG_R3,0)]:u.reg_write(k,val)
 if n==1:u.reg_write(UC_ARM_REG_R2,0 if v==3 else fast)
 if n==2:u.mem_write(0x1167000,bytes([1,2,3,4]));u.reg_write(UC_ARM_REG_R0,0x1167000)
 if n==3:u.reg_write(UC_ARM_REG_R1,page2)
 if n==4:u.reg_write(UC_ARM_REG_R2,control);u.reg_write(UC_ARM_REG_R3,mode)
 if n==5:u.reg_write(UC_ARM_REG_R0,0 if v==0 else color)
 if n==8:u.reg_write(UC_ARM_REG_R1,one if v==1 else two if v==3 else absent)
 if n in (6,7) and v==3:u.reg_write(UC_ARM_REG_R2,0x1170000)
 if n==9:u.reg_write(UC_ARM_REG_R2,color if v==3 else 0)
 if n==10:u.reg_write(UC_ARM_REG_R2,0 if v==1 else color);u.reg_write(UC_ARM_REG_R3,int(v==3))
 def hook(uc,addr,size,user):
  if addr==stop:stopped[0]=True;uc.emu_stop()
  elif addr==0x762a8:ret(item if v else 0)
  elif addr==0x760a8:trace.append('blink:'+string(reg(1)));ret()
  elif addr==0x75050:trace.append('maprgb:'+str(reg(0)));ret(7)
  elif addr==0x74c18:trace.append('mapstr:'+string(reg(0)));ret(0x44332211)
  elif addr==0x75ee8:trace.append('translate:'+string(reg(0)));ret(3)
  elif addr==0x13fe004:trace.append('bind:'+str(reg(2)));ret()
  elif addr==0x13fe000:trace.append('page:'+('1' if reg(0)==page1 else '2'));ret(one if reg(0)==page1 else two)
  elif addr==0x13fe008:trace.append('ledcast');ret(control if v==3 else 0)
  elif addr==0x13fe00c:ret(alias)
  elif addr in (0x15cd4,0x15ce8):trace.append('getter:'+str(int(n==7)))
  elif addr==0x120e24:trace.append('alias:1');ret()
  elif addr in (0x13fe010,0x13fe014):trace.append('setter:'+str(int(n==7)));ret()
  elif addr==0x74ce4:trace.append('enum:'+string(r(reg(0)))+':'+str(reg(1)));ret(9)
  elif addr==0x16360:trace.append('color:'+str(reg(1)));ret()
  elif addr==0xb0f8:
   a=string(reg(0));b=string(reg(1));ret(0 if a==b else 1)
  elif addr==0xb02c:ret(len(string(reg(0))))
  elif addr==0xb170:u.mem_write(reg(0),bytes(u.mem_read(reg(1),reg(2))));ret(reg(0))
 u.hook_add(UC_HOOK_CODE,hook);u.emu_start(ADDRESSES[n-1],stop,count=5000)
 # Unicorn stops at the explicit end address before the hook in some releases.
 assert u.reg_read(UC_ARM_REG_PC)==stop or stopped[0], "instruction budget exhausted"
 result=u.reg_read(UC_ARM_REG_R0) if n in (2,5,8) else 0
 if n==8:result=1 if result==page1 else 2 if result==page2 else 0
 return f'{result}|{r(obj+73744) if n==3 else 0}|{string(item+40)}|{int(r(item)!=0)}|'+ ';'.join(trace)
def main():
 path=pathlib.Path(sys.argv[1]);assert hashlib.sha256(path.read_bytes()).hexdigest()==ELF_SHA
 result=[{'method':n,'variant':v,'expected':observe(path,n,v)} for n in range(1,11) for v in range(4)]
 pathlib.Path(sys.argv[2]).write_text(json.dumps({'elf_sha256':ELF_SHA,'boundary_stubs':'findItem scripted hit/miss; ColorMapping captures; panel virtual dispatch captures; Core AliasParam not executed on ARM; actual native loads/branches/stores execute','cases':result},indent=2)+'\n');print('40 original ARM cases')
if __name__=='__main__':main()
