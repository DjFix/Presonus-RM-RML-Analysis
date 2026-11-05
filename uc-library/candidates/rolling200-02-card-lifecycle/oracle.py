"""Offline original-range execution. All imports are finite private-memory hooks."""
from pathlib import Path
import hashlib,json,struct
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
R=Path(__file__).resolve().parents[3]
A=Path(__file__).resolve().parent
E=R/'evidence/recovery/2026-11-05/rolling200-02/card-lifecycle';E.mkdir(parents=True,exist_ok=True)
P=R/'temp/recovery-work/rolling200-02/implementation-plan01/packets-card-lifecycle02/packets'
elf=R/'rootfs/RML16AI_Rack_13731/home/root/mixer';raw=elf.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
with elf.open('rb') as f:
 ef=ELFFile(f);segments=[(int(s['p_vaddr']),s.data(),int(s['p_memsz'])) for s in ef.iter_segments() if s['p_type']=='PT_LOAD'];sec=ef.get_section(12);sh=dict(sec.header)
OBJ=0x1000000;STACK=0x1100000;HEAP=0x1200000;STOP=0x1300000;GLOBAL=0x495368
cases=[];ranges=[];lines=[]
for i in range(2,7):
 req=json.loads((P/f'rolling200_02_card_lifecycle_{i:02}'/'request.json').read_text());t=req['targets'][0];start=t['address'];end=start+t['size'];off=sh['sh_offset']+start-sh['sh_addr'];code=raw[off:off+t['size']]
 ranges.append(dict(**t,section=12,file_offset=off,range_sha256=hashlib.sha256(code).hexdigest()))
 for lazy in (0,1):
  for seed in (0,0xa5,255):
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM);pages=set()
   for a,b,n in segments:
    for pg in range(a&~4095,(a+n+4095)&~4095,4096):
     if pg not in pages:u.mem_map(pg,4096);pages.add(pg)
    u.mem_write(a,b)
   for a,n in ((OBJ,4096),(STACK,8192),(HEAP,4096),(STOP,4096)):u.mem_map(a,n)
   u.mem_write(OBJ,bytes([seed])*104);u.mem_write(GLOBAL,struct.pack('<I',0 if lazy else HEAP))
   u.reg_write(UC_ARM_REG_R0,OBJ);u.reg_write(UC_ARM_REG_SP,STACK+4096);u.reg_write(UC_ARM_REG_LR,STOP)
   events=[];writes=[];done=[False];freed=[]
   def ret():u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
   def hook(uc,pc,size,data):
    r0=u.reg_read(UC_ARM_REG_R0);r1=u.reg_read(UC_ARM_REG_R1)
    if pc==STOP:done[0]=True;u.emu_stop();return
    if start<=pc<end:return
    if pc==0xa4b38:assert r0==OBJ;events.append('base');ret()
    elif pc==0xa7e4:assert r0==456;events.append('new');u.reg_write(UC_ARM_REG_R0,HEAP);ret()
    elif pc==0xa2e64:assert r0==HEAP;events.append('spi');ret()
    elif pc==0x126cfc:assert r0==HEAP;events.append('registry');ret()
    elif pc in (0xa30d4,0xa2fe0):
     assert r0==HEAP and r1==OBJ;events.append('register' if pc==0xa30d4 else 'unregister');ret()
    elif pc==0xac10:
     assert r0==OBJ and i==4;freed.append(r0);events.append('delete');ret()
    else:raise AssertionError(('unapproved execution',hex(pc)))
   def write(uc,access,a,n,value,data):
    assert (OBJ<=a and a+n<=OBJ+104) or (STACK<=a and a+n<=STACK+8192) or (HEAP<=a and a+n<=HEAP+456) or (a==GLOBAL and n==4),(hex(a),n)
    if OBJ<=a<OBJ+104:writes.append([a-OBJ,n,value])
   u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write);u.emu_start(start,STOP+4,count=1000);assert done[0]
   image=bytes(u.mem_read(OBJ,104));constructor=i in (2,3)
   if constructor:
    assert struct.unpack_from('<II',image,16)==(0xffffffff,0xffffffff)
    assert image[24:73]==bytes(49) and image[76:96]==bytes(20)
    assert image[73:76]==bytes([seed])*3 and image[96:]==bytes([seed])*8
   else:assert image[16:]==bytes([seed])*88
   assert len(freed)==(i==4)
   expected=(['base'] if constructor else [])+(['new','spi','registry'] if lazy else [])+(['register'] if constructor else ['unregister'])+(['delete'] if i==4 else [])
   assert events==expected
   c=dict(mangled=t['mangled'],variant=t['mangled'].split('TCard')[1][:2],lazy=lazy,seed=seed,events=events,writes=writes,image=image.hex(),native_delete_calls=len(freed),returned=True);cases.append(c)
   lines.append(f"{c['variant']} {lazy} {seed} {len(freed)} {image.hex()} {';'.join(events)}")
(E/'lifecycle-native.json').write_text(json.dumps(dict(elf=str(elf.relative_to(R)),elf_sha256=hashlib.sha256(raw).hexdigest(),ranges=ranges,cases=cases,limitations=['Core and SPI bodies intercepted as explicit imports; no native Core recovery','Allocation exception unwind not executed; finite successful-import domain only','Only target ranges execute; no hardware, syscall, network or host guest-memory pointer passthrough']),indent=2)+'\n')
(E/'lifecycle-fixtures.txt').write_text('\n'.join(lines)+'\n')
print(f'{len(cases)} lifecycle original executions; all five independent ranges; actual D0 allocator PC observed')
