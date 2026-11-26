import hashlib,json,struct
from pathlib import Path
from io import BytesIO
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
TASK=Path(__file__).parent.name
PACKET=Path('temp/recovery-work/sqlite-issued/packet-sol61')/TASK/'CONTEXT.json'
def observe():
 out=[]
 for row in json.loads(PACKET.read_text())['originals']:
  o=row['original']; raw=Path(o['elf_path']).read_bytes(); assert hashlib.sha256(raw).hexdigest()==o['elf']
  elf=ELFFile(BytesIO(raw)); sym=elf.get_section_by_name('.symtab').get_symbol_by_name(o['mangled'])[0]; sec=elf.get_section(sym['st_shndx'])
  assert (sym['st_value'],sym['st_size'],sym['st_shndx'])==(o['address'],o['size'],o['section'])
  off=sec['sh_offset']+o['address']-sec['sh_addr']; assert off==o['file_offset']
  assert hashlib.sha256(raw[off:off+o['size']]).hexdigest()==o['range_sha256']
  sender='object_change' in TASK
  cases=[(m,ids,swap) for m in [0,7,13,255,-1] for ids in [[],[1],[1,2,1]] for swap in ([0,1] if m==13 and ids else [0])] if sender else [(0,[],0),(0,[1,2,1],0)]
  for msg,ids,swap in cases:
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x500000)
   for seg in elf.iter_segments():
    if seg['p_type']=='PT_LOAD':u.mem_write(seg['p_vaddr'],seg.data())
   u.mem_map(0x800000,0x20000); obj,items,newitems,vt,h,stop=0x801000,0x802000,0x803000,0x804000,0x805000,0x81e000
   def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
   def r(a):return struct.unpack('<I',u.mem_read(a,4))[0]
   u.mem_write(obj,b'\xa5'*64)
   for i in [1,2,3]:w(0x806000+i*16,vt)
   w(vt,h);w(vt+4,h+4)
   for i,n in enumerate(ids):w(items+4*i,0x806000+n*16)
   w(newitems,0x806030);w(obj+16,items if ids else 0);w(obj+20,len(ids));w(obj+24,5 if ids else 0)
   events=[];boundary=[]
   target=o['address']; isctor=TASK.startswith('sqlite_mappable_c')
   branch=next((target+i for i in range(0,o['size']-4,4) if raw[off+i+3]==0xeb),None) if not sender else None
   provider=None
   if branch is not None:
    instruction=r(branch);imm=instruction&0xffffff;imm=imm-(1<<24) if imm&(1<<23) else imm;provider=branch+8+imm*4
   def hook(machine,pc,size,data):
    if pc in [h,h+4]:
     n=(machine.reg_read(UC_ARM_REG_R0)-0x806000)//16;events.append([0 if pc==h else 1,n,0 if pc==h else msg])
     if swap and pc==h and len(events)==len(ids):w(obj+16,newitems);w(obj+20,1)
    elif pc==provider:
     assert machine.reg_read(UC_ARM_REG_R0)==obj+12
     if isctor:
      assert machine.reg_read(UC_ARM_REG_R1)==0
      assert [r(obj+i) for i in [4,8,16,20,24,28]]==[0,0,0,0,0,5];boundary.append('resize-zero')
     else:
      assert r(obj)==struct.unpack('<I',raw[off+o['size']-4:off+o['size']])[0]
      boundary.append(['vector-dtor',len(ids),bool(r(obj+16))])
    else:return
    machine.reg_write(UC_ARM_REG_PC,machine.reg_read(UC_ARM_REG_LR))
   u.hook_add(UC_HOOK_CODE,hook)
   for reg,v in [(UC_ARM_REG_R0,obj),(UC_ARM_REG_R1,msg&0xffffffff),(UC_ARM_REG_SP,0x81d000),(UC_ARM_REG_LR,stop)]:u.reg_write(reg,v)
   u.emu_start(target,stop,count=5000);assert u.reg_read(UC_ARM_REG_PC)==stop
   if isctor:assert [r(obj+i) for i in [4,8,16,20,24,32,36]]==[0]*7
   out.append(dict(role=o['role'],args=[msg,','.join(map(str,ids)) or '-',swap],events=events,boundary=boundary))
 return out
if __name__=='__main__':print(json.dumps(observe(),indent=2))
