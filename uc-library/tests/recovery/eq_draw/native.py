"""Exact app ARM target oracle; provider boundaries intercepted, never guest Core."""
import hashlib,json,struct,itertools
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
R=Path(__file__).resolve().parents[4];ELF=R/'rootfs/CS18_v13840/home/root/surface';RAW=ELF.read_bytes();SHA=hashlib.sha256(RAW).hexdigest();assert SHA=='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
NAMES=['_ZN8Presonus9EQControl4drawERKN4Core8Portable9DrawEventE','_ZN8Presonus17BackgroundPainter5paintERKN4Core5TRectIiEERKNS1_8Portable9DrawEventERKNS6_5StyleE']
RANGES=[]
with ELF.open('rb') as f:
 e=ELFFile(f)
 for name in NAMES:
  s=next(s for s in e.get_section_by_name('.symtab').iter_symbols() if s.name==name);sec=e.get_section(s['st_shndx']);off=sec['sh_offset']+s['st_value']-sec['sh_addr'];RANGES.append(dict(mangled=name,address=s['st_value'],size=s['st_size'],section=sec.name,file_offset=off,sha256=hashlib.sha256(RAW[off:off+s['st_size']]).hexdigest()))
O=0x400000;E=0x410000;G=0x420000;V=0x430000;B=0x440000;P=0x450000;S=0x460000;I=0x470000;T=0x480000;STACK=0x500000;STOP=0x600000
CLIPS=[[0,0,24,20],[10,8,14,12],[20,16,24,20],[14,8,18,12]]
def execute(c,base=False):
 mode,primary,frames,selected,enabled,on,painters,bg,clip,custom=c
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x300000)
 with ELF.open('rb') as f:
  for seg in ELFFile(f).iter_segments():
   if seg['p_type']=='PT_LOAD':u.mem_write(seg['p_vaddr'],seg.data())
 u.mem_protect(0,0x300000,5);u.mem_map(O,0x90000);u.mem_map(STACK,0x10000);u.mem_map(STOP,0x1000)
 def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def r(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 def si(v):return v if v<2**31 else v-2**32
 def ints(a,n):return list(struct.unpack('<'+'i'*n,u.mem_read(a,n*4)))
 def ret(v=0):u.reg_write(UC_ARM_REG_R0,v&0xffffffff);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def rect(a,v):u.mem_write(a,struct.pack('<4i',*v))
 w(E,G);rect(E+4,CLIPS[clip]);w(G,V);w(V+0x14,STOP+4);w(V+0x28,STOP+8)
 w(S,0xff102030);w(S+4,0xff405060);w(O+0x6c,0xff708090);w(O+0x68,6)
 w(O+0x48,P if primary>=0 else 0);w(P,V+0x100);w(V+0x144,STOP+12)
 w(O+0x70,1);w(O+0x78,P+0x1000);w(O+0x7c,1);w(O+0xf0,B);w(P+0x1014,P+0x100 if selected>=0 else 0);w(P+0x100,V+0x100)
 u.mem_write(B+9,bytes([enabled]));w(B+0x18,12);w(B+0x1c,10)
 for i,fc in enumerate([frames,3,2]):
  w(I+i*0x100+8,fc or 1);w(I+i*0x100+12,8 if i==0 else 24);w(I+i*0x100+16,(4*(fc or 1)) if i==0 else 20)
 if frames:w(B+0x20 if custom else O+0x64,I)
 if bg:w(O+0x60,I+0x100)
 w(O+0x114,0 if mode==3 else I+0x200);u.mem_write(O+0x118,bytes([int(mode==1),int(mode!=0)]))
 if painters:
  w(O+0x104,T);w(O+0x108,1 if painters==1 else 2)
  for i in range(2):
   w(T+i*4,T+0x100+i*16);w(T+0x100+i*16,V+0x200+i*16);w(V+0x200+i*16,0x6a5b8 if painters==1 else STOP+16+i*4)
 trace=[];curve=[];writes=[];pcs=[]
 def code(uc,a,size,_):
  q=[uc.reg_read(z) for z in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]];x,y,z,t=q
  if a==STOP:uc.emu_stop();return
  if a==STOP+4:trace.append([1,*ints(y,4),r(z)]);ret(1)
  elif a==STOP+8:trace.append([2,(z-I)//0x100,*ints(y,2),*ints(t,4)]);ret(1)
  elif a==STOP+12:ret(struct.unpack('<I',struct.pack('<f',float(primary if x==P else selected)))[0])
  elif a in [STOP+16,STOP+20]:
   assert y==O+0x2c and z==E and t==S
   trace.append([4,(a-STOP-16)//4]);ret()
  elif a==0x10e9a8:ret(O+0x2c)
  elif a==0x10f4b4:ret(S)
  elif a==0x10e9bc:rect(y,[0,0,24,20]);ret(y)
  elif a==0x1877e0:
   value=struct.unpack('<f',struct.pack('<I',x))[0];ret(int(value>struct.unpack('<f',struct.pack('<I',y))[0]))
  elif a==0x1864b8:ret(int(si(x)/si(y)))
  elif a==0x102d50:ret(x)
  elif a==0x1018e8:
   assert r(z)==0, hex(r(z)) # native static black argument
   ret(1)
  elif a==0x6c1bc:
   assert y==E
   curve.append([r(z),t]);
   if enabled and CLIPS[clip][1] <= 10 < CLIPS[clip][3]:trace.append([3,r(z)])
   ret()
  elif a==0x6ab9c:ret(on)
  elif any(v['address']<=a<v['address']+v['size'] for v in RANGES):pcs.append(a)
  else:raise AssertionError(('unbound guest instruction',hex(a),list(map(hex,q))))
 def write(uc,access,a,size,value,_):
  if O<=a<O+0x120:writes.append([a-O,size,value])
 u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
 rect(O+0x2c,[3,4,27,24]);u.reg_write(UC_ARM_REG_SP,STACK+0xff00);u.reg_write(UC_ARM_REG_LR,STOP)
 for reg,val in zip([UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3],[O,O+0x2c,E,S] if base else [O,E,0,0]):u.reg_write(reg,val)
 u.emu_start(0x6a5b8 if base else 0x6eac4,STOP,count=20000)
 assert u.reg_read(UC_ARM_REG_PC)==STOP
 return {'input':c,'base':base,'trace':trace,'dirty':u.mem_read(O+0x118,1)[0],'curve_calls':curve,'native_writes':writes,'target_instruction_count':len(pcs)}
def cases():
 cs=[]
 for mode,primary,frames,selected in itertools.product(range(4),[-1,0,1],[0,1,2,4],[-1,0,1]):cs.append([mode,primary,frames,selected,1,1,0,0,0,1])
 for clip,painters,bg,enabled,on,custom in itertools.product(range(4),range(3),range(2),range(2),range(2),range(2)):cs.append([0,1,4,1,enabled,on,painters,bg,clip,custom])
 cs += [[0,1,f,1,1,1,0,0,k,1] for f in [1,2,4] for k in range(4)]
 return [execute(c) for c in cs]+[execute([0,0,0,-1,0,0,0,0,k,0],True) for k in range(4)]
if __name__=='__main__':
 data={'elf_sha256':SHA,'ranges':RANGES,'cases':cases()};Path(__file__).with_name('fixtures.json').write_text(json.dumps(data,indent=2)+'\n');print(len(data['cases']))
