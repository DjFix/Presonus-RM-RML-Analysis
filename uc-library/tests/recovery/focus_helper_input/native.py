"""Private ARM execution: only four app methods and bound runtime execute.
Core, strcmp and virtual provider boundaries are observed and intercepted.
No guest Core, host syscalls, devices, or C++ supplies expected observations.
"""
import hashlib,json,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
R=Path(__file__).resolve().parents[4]; T=Path(__file__).resolve().parent
ELF=R/'rootfs/CS18_v13840/home/root/surface'
SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
RAW=ELF.read_bytes();assert hashlib.sha256(RAW).hexdigest()==SHA
NAMES=['_ZN8Presonus17FocusHelperButton12paramChangedEPN4Core8Portable9ParameterEi','_ZN8Presonus17FocusHelperButton4drawERKN4Core8Portable9DrawEventE','_ZN8Presonus17FocusHelperButton12restoreFocusEv','_ZN8Presonus17FocusHelperButton6onIdleEv','__aeabi_f2iz']
RANGES=[]
with ELF.open('rb') as f:
 e=ELFFile(f);syms={s.name:s for s in e.get_section_by_name('.symtab').iter_symbols()}
 for name in NAMES:
  s=syms[name];sec=e.get_section(s['st_shndx']);off=sec['sh_offset']+s['st_value']-sec['sh_addr'];RANGES.append(dict(mangled=name,address=s['st_value'],size=s['st_size'],file_offset=off,section=sec.name,section_index=s['st_shndx'],sha256=hashlib.sha256(RAW[off:off+s['st_size']]).hexdigest()))
EXPECTED=['7dd0edd7cce0be1899e665c24937ba4e338ed73402ada45de8bd10ffa65e1eda','d3d004dab714e64af25004dd8c2a94598d70a7c5afaf290c496687217385df1f','467a83c3718df9703e3087e302659abd3ce8be61c4946d45be8c09ec3146f568','112f8375c408b97a1585871d6ae6fe94094c896243e4439d6d66acbf5369604d','73908d204e4625c30fc21dff9a2f817e26c53d161164a032bd229a9dcdd6edee']
assert [x['sha256'] for x in RANGES]==EXPECTED
OBJ=0x400000;PAR=0x401000;PARENT=0x402000;CHILD=0x403000;VT=0x410000;ROOT=0x420000;STR=0x430000;STOP=0x600000;STACK=0x500000

def execute(c):
 mode,bits,value,active,msg,parent,root,names=c
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x300000)
 with ELF.open('rb') as f:
  for seg in ELFFile(f).iter_segments():
   if seg['p_type']=='PT_LOAD':u.mem_write(seg['p_vaddr'],seg.data())
 u.mem_protect(0,0x300000,5);u.mem_map(OBJ,0x40000);u.mem_map(STACK,0x10000);u.mem_map(STOP,0x1000)
 def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def r(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 w(OBJ,VT);w(OBJ+0xe4,value);u.mem_write(OBJ+0xe8,bytes([active]));w(OBJ+0xec,STR);u.mem_write(STR,b'target\0')
 w(PAR,VT+0x100);w(VT+0x144,STOP+4);w(VT+0x64,STOP+8);w(VT+0x14,STOP+12);w(PARENT,VT+0x200);w(VT+0x200,STOP+16);w(ROOT,VT+0x300);w(VT+0x370,STOP+20)
 w(PARENT+0x48,CHILD+0x1000);w(PARENT+0x4c,len(names))
 for i,n in enumerate(names):
  child=CHILD+i*0x100;w(CHILD+0x1000+4*i,child);u.mem_write(child+8,(b'target' if n else b'other')+b'\0')
 trace=[];focus=[];requests=0;frames=0;writes=[];pcs=[]
 def code(uc,a,size,_):
  nonlocal requests,frames
  x=uc.reg_read(UC_ARM_REG_R0);y=uc.reg_read(UC_ARM_REG_R1)
  result=0
  if a==STOP:uc.emu_stop();return
  if a==0xf8768:trace.append(['Control.paramChanged',msg])
  elif a==STOP+4:trace.append(['Parameter.getValue']);result=bits
  elif a==0xfb2a4:trace.append(['Button.draw'])
  elif a==STOP+8:trace.append(['RadioButton.isOn']);result=int(bits==0x3f800000)
  elif a==0x10ea60:trace.append(['View.isEnabled']);result=msg
  elif a==0xf76b4:trace.append(['Control.drawFocusFrame']);frames+=1
  elif a==0xf8588:trace.append(['Control.onIdle'])
  elif a==0x10e8d0:
   assert u.mem_read(OBJ+0xe8,1)==b'\0';trace.append(['getParent']);result=PARENT if parent else 0
  elif a==STOP+16:
   assert y==0x56696577;trace.append(['castTo.View']);result=PARENT if parent in [2,3] else 0
  elif a==0xb0f8:
   def string(p):
    out=b''
    for i in range(128):
     b=bytes(u.mem_read(p+i,1))
     if b==b'\0':return out
     out+=b
    raise AssertionError('unbounded string')
   result=int(string(x)!=string(y));trace.append(['strcmp',(x-CHILD-8)//0x100,result])
  elif a==STOP+12:
   assert x==OBJ, 'getRootView receiver must be button (native r7), never child r6'
   assert u.mem_read(OBJ+0xe8,1)==b'\0';requests+=1;result=ROOT if root else 0;trace.append(['getRootView'])
  elif a==STOP+20:
   assert u.mem_read(OBJ+0xe8,1)==b'\0';focus.append((y-CHILD)//0x100);trace.append(['setFocusView',focus[-1]])
  else:
   assert any(z['address']<=a<z['address']+z['size'] for z in RANGES),(hex(a),'unbound guest instruction')
   pcs.append(a);return
  uc.reg_write(UC_ARM_REG_R0,result);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
 def write(uc,access,a,size,v,_):
  assert STACK<=a<STACK+0x10000 or a==OBJ+0xe8,(hex(a),size,v)
  if a==OBJ+0xe8:writes.append([a-OBJ,size,v])
 u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
 u.reg_write(UC_ARM_REG_SP,STACK+0xf000);u.reg_write(UC_ARM_REG_LR,STOP);u.reg_write(UC_ARM_REG_R0,OBJ);u.reg_write(UC_ARM_REG_R1,PAR);u.reg_write(UC_ARM_REG_R2,msg)
 u.emu_start(RANGES[mode]['address'],STOP+0x100,count=20000)
 assert u.reg_read(UC_ARM_REG_PC)==STOP
 output=[u.mem_read(OBJ+0xe8,1)[0],frames,requests,*focus]
 return {'input':c,'expected':output,'trace':trace,'writes':writes,'executed_pc_sha256':hashlib.sha256(struct.pack('<'+'I'*len(pcs),*pcs)).hexdigest()}

def generate():
 cases=[]
 bits=[0,0x80000000,1,0x80000001,0x3f000000,0xbf000000,0x3f800000,0xbff33333,0x402ccccd,0x4effffff,0x4f000000,0xcf000000,0xcf000001,0x7f800000,0xff800000,0x7fc00000,0xffc00000,0x7f800001,0xffffffff]
 for b in bits:
  for v in [0,1,-1,2,-2,2147483520,-2147483520,2147483647,-2147483648]:
   for active in [0,1]:cases.append(execute([0,b,v,active,3,0,0,[]]))
 for msg in [0,1,2,4,6]:cases.append(execute([0,0x3f800000,1,0,msg,0,0,[]]))
 for on in [0,0x3f800000]:
  for enabled in [0,1]:cases.append(execute([1,on,1,0,enabled,0,0,[]]))
 for mode in [2,3]:
  for active in [0,1]:
   for parent in [0,1,2]:
    for root in [0,1]:
     for names in [[],[0],[1],[0,1,0],[1,1,1],[1,0,1]]:cases.append(execute([mode,0,1,active,3,parent,root,names]))
 for mode in [2,3]:
  for active in [0,1]:cases.append(execute([mode,0,1,active,3,3,1,[]]))
 return {'elf_sha256':SHA,'ranges':RANGES,'cases':cases}
if __name__=='__main__':(T/'fixtures.json').write_text(json.dumps(generate(),indent=2)+'\n')
