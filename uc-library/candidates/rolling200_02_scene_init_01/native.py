"""Exact ARM init and admitted name helper; only pinned CCL boundaries intercepted."""
from pathlib import Path
import hashlib,json,struct
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
from elftools.elf.elffile import ELFFile
ROOT=Path(__file__).resolve().parents[3]
C=Path(__file__).parent
raw=(ROOT/'rootfs/RML16AI_Rack_13731/home/root/mixer').read_bytes()
sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(raw)=='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
with (ROOT/'rootfs/RML16AI_Rack_13731/home/root/mixer').open('rb') as f:
 e=ELFFile(f);segments=[(s['p_vaddr'],s['p_memsz'],s.data()) for s in e.iter_segments() if s['p_type']=='PT_LOAD'];sym=next(s for s in e.get_section_by_name('.symtab').iter_symbols() if s.name=='_ZN8Presonus22StormMixSceneComponent4initEv');sec=e.get_section(sym['st_shndx']);off=sec['sh_offset']+sym['st_value']-sec['sh_addr']
 assert (sym['st_value'],sym['st_size'],sec.name,off)==(0x73394,108,'.text',0x6b394)
assert sha(raw[438800:438864])=='a4685df65b258a26b06989344195de989e9f6cbc71c7efa511a377121101c317'
body=raw[off:off+108];assert sha(body)=='514a8f02795e9e4aa64f9f4eae12bf0c9787a7ce0c8c0c237324788763e709ac'
base=0x60000000;params=0x60010000;vt=0x60020000;stack=0x70000000;stop=0x71000000;dispatch=stop+0x100
cases=[]
for mask in range(256):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
 lo=min(a for a,n,d in segments)&~4095;hi=(max(a+n for a,n,d in segments)+4095)&~4095
 u.mem_map(lo,hi-lo)
 for a,n,d in segments:u.mem_write(a,d)
 for a,n in [(base,0x30000),(stack,0x10000),(stop,0x1000)]:u.mem_map(a,n)
 u.mem_write(0x73394,body)
 def w(a,v):u.mem_write(a,struct.pack('<I',v))
 w(vt+0x74,dispatch)
 for i in range(8):w(params+256*i,vt)
 trace=[];lookups=[];indices=[];pcs=[];writes=[];namebuf=[None]
 def hook(u,pc,size,_):
  a=u.reg_read(UC_ARM_REG_R0);b=u.reg_read(UC_ARM_REG_R1);c=u.reg_read(UC_ARM_REG_R2)
  if pc==stop:u.emu_stop();return
  if 0x73394<=pc<0x73400:pcs.append(pc);return
  if 0x73210<=pc<0x73248:
   if pc==0x73210:
    assert b==base and 0<=c<8;indices.append(c);namebuf[0]=a
   return
  if pc==0x119c4c:
   assert a==base;lookups.append(b);assert 10<=b<=17
   u.reg_write(UC_ARM_REG_R0,params+256*(b-10) if mask&(1<<(b-10)) else 0)
  elif pc in (0x1debc,0x3987c):
   def string(addr):return bytes(u.mem_read(addr,256)).split(b'\0')[0]
   if pc==0x1debc:
    assert u.reg_read(UC_ARM_REG_LR)==0x73230;assert string(b)==b'Mix Scene';text=string(b)
   else:
    assert u.reg_read(UC_ARM_REG_LR)==0x73240;assert string(b)==b' %i'
    text=string(a)+(' '+str(struct.unpack('<i',struct.pack('<I',c))[0])).encode()
   assert stack<=a and a+32<=stack+0x10000
   u.mem_write(a,text[:31]+b'\0');u.reg_write(UC_ARM_REG_R0,a)
  elif pc==dispatch:
   assert b==namebuf[0] and c==0
   i=(a-params)//256;assert a==params+256*i and mask&(1<<i)
   text=bytes(u.mem_read(b,32)).split(b'\0')[0].decode();trace.append(f'{10+i}:{text}:{c}')
  else:raise AssertionError(hex(pc))
  u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def write(u,access,a,size,value,_):
  assert stack<=a and a+size<=stack+0x10000,(hex(a),size)
  writes.append([a,size,value])
 u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
 u.reg_write(UC_ARM_REG_SP,stack+0x8000);u.reg_write(UC_ARM_REG_R0,base);u.reg_write(UC_ARM_REG_LR,stop)
 before=bytes(u.mem_read(base,0x30000));u.emu_start(0x73394,stop+4,count=4000)
 assert u.reg_read(UC_ARM_REG_PC)==stop and before==bytes(u.mem_read(base,0x30000))
 assert lookups==list(range(10,18));assert indices==[i for i in range(8) if mask&(1<<i)]
 assert 0x73394 in pcs and 0x733fc in pcs
 cases.append(dict(mask=mask,trace=trace,lookups=lookups,helper_indices=indices,visited_pcs=sorted(set(pcs)),native_stack_writes=writes))
(C/'fixtures.tsv').write_text(''.join(str(c['mask'])+' '+'|'.join(c['trace'])+'\n' for c in cases))
(C/'native.json').write_text(json.dumps(dict(elf_sha256=sha(raw),address=0x73394,size=108,section='.text',file_offset=off,range_sha256=sha(body),boundary_pcs={'lookup':0x119c4c,'name_helper':0x73210,'ccl_string_construct':0x1debc,'ccl_string_append':0x3987c,'parameter_fromString':dispatch,'stop':stop},limitations='Real init and createDefaultName instructions; CCL string construction/format and lookup/fromString intercepted; not native Core execution or original layout verification',cases=cases),indent=2)+'\n')
print('256 full-range native executions passed; eight lookup tags, conditional helper/dispatch, edit=false, guarded native stack writes')
