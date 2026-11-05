"""Execute original app lifecycle instructions; never execute Core binary bodies."""
import hashlib,json,pathlib,struct,sys
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
from elftools.elf.elffile import ELFFile
ROOT=pathlib.Path(__file__).resolve().parents[5]
PACKETS=pathlib.Path('temp/recovery-work/rolling200-02/next-implementation08/prepared09-eq_lifecycle08/packets')
OUT=pathlib.Path('evidence/recovery/2026-11-05/rolling200-02/eq-lifecycle/native.json')
ELF='rootfs/CS18_v13840/home/root/surface';SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
OBJ=0x400000;DATA=0x410000;STACK=0x500000;SP=STACK+0x8000;STOP=0x600000
HELPER=0x6c348;REMOVE=0x11e2e0;DELETE_ARRAY=0xaec4;DELETE=0xad5c;BITMAP=0xeefec
BOUNDARIES={REMOVE,DELETE_ARRAY,DELETE,BITMAP,0x11f77c,0x6f534,0x6f3cc,0xfb15c}

def bitmap_vtable():
 with (ROOT/ELF).open('rb') as f:
  elf=ELFFile(f);symbols={s.name:s for s in elf.get_section_by_name('.symtab').iter_symbols()}
  v=symbols['_ZTVN4Core8Portable6BitmapE'];d=symbols['_ZN4Core8Portable6BitmapD0Ev'];section=elf.get_section(v['st_shndx'])
  offset=section['sh_offset']+v['st_value']-section['sh_addr'];raw=(ROOT/ELF).read_bytes()[offset:offset+v['st_size']]
  words=struct.unpack('<4I',raw);assert words[3]==d['st_value']==BITMAP
  return dict(mangled=v.name,address=v['st_value'],size=v['st_size'],section=section.name,file_offset=offset,sha256=hashlib.sha256(raw).hexdigest(),words=list(words),deleting_destructor=d.name,target=BITMAP,scope='Data and original symbol identity only; no Core binary execution')

def verified():
 raw=(ROOT/ELF).read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
 result=[]
 with (ROOT/ELF).open('rb') as f:
  elf=ELFFile(f)
  for i in range(1,4):
   j=json.loads((ROOT/PACKETS/f'rolling200_02_eq_lifecycle_{i:02d}/native-context.json').read_text());b=j['bodies'][j['roots'][0]]
   sec=elf.get_section(b['section_index']);offset=sec['sh_offset']+b['address']-sec['sh_addr']
   assert offset==b['file_offset'] and sec.name==b['section']
   code=raw[offset:offset+b['size']];assert hashlib.sha256(code).hexdigest()==b['bytes_sha256']
   result.append(({k:b[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']},code))
  # Bound existing helper is independently hash-verified by its sealed packet.
  j=json.loads((ROOT/'temp/recovery-work/rolling200-02/next-implementation08/expand09-eq-remove-observer/native-context.json').read_text());b=j['bodies'][j['roots'][0]]
  assert b['address']==HELPER
  sec=elf.get_section(b['section_index']);offset=sec['sh_offset']+b['address']-sec['sh_addr'];assert offset==b['file_offset']
  code=raw[offset:offset+b['size']];assert hashlib.sha256(code).hexdigest()==b['bytes_sha256']
  result.append(({k:b[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']},code))
 return result

def execute(bodies,variant,count,pattern,mask,constructed):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
 pages={a&~4095 for a in BOUNDARIES}
 for b,_ in bodies:
  pages.update(range(b['address']&~4095,(b['address']+b['size']+4095)&~4095,4096))
 for page in sorted(pages):u.mem_map(page,4096)
 for b,code in bodies:u.mem_write(b['address'],code)
 for a,n in [(OBJ,4096),(DATA,65536),(STACK,65536),(STOP,4096)]:u.mem_map(a,n)
 def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def r(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 bands=DATA;curves=DATA+0x1008;params=[DATA+0x2000+i*0x100 for i in range(9)];images=[DATA+0x3000+i*0x100 for i in range(3)]
 allocations={OBJ:0};removals=[];trace=[];writes=[];events=[]
 def refs():return [r(p+0x34) for p in images]
 for i in range(count):
  ids=[0 if pattern==0 else s+1 if pattern==1 else 1 if pattern==2 else s+1 if (s+i)%2 else 0 for s in range(6)]
  if constructed and i==0:ids[:3]=[9,8,7]
  for s,v in enumerate(ids):w(bands+24*i+4*s,params[v-1] if v else 0)
 w(OBJ+0x78,bands);w(OBJ+0x7c,count)
 if mask&1:
  for offset,label in [(0x98,1),(0x9c,2)]:
   pointer=DATA+0x4000+label*0x100;w(OBJ+offset,pointer);allocations[pointer]=label
 if mask&2:
  w(OBJ+0xf0,curves);w(curves-4,count)
  for i in range(count):
   pointer=DATA+0x5000+i*0x100;w(curves+40*i+12,pointer);allocations[pointer]=3+i
   image=images[i%3];w(curves+40*i+32,image);w(image+0x34,r(image+0x34)+1)
  w(OBJ+0x60,images[0]);w(OBJ+0x64,images[1]);w(images[0]+0x34,r(images[0]+0x34)+1);w(images[1]+0x34,r(images[1]+0x34)+1)
 if mask&4:
  output=DATA+0x6000;vtable=DATA+0x6100;w(OBJ+0x114,output);w(output,vtable);w(vtable+4,BITMAP);allocations[output]=10
 before_shared=None;calls=[];object_delete_instruction=None
 def hook(uc,a,size,user):
  nonlocal before_shared,object_delete_instruction
  if a in BOUNDARIES:
   receiver=uc.reg_read(UC_ARM_REG_R0);lr=uc.reg_read(UC_ARM_REG_LR);calls.append([a,receiver,lr])
   if a==REMOVE:
    assert receiver in params and uc.reg_read(UC_ARM_REG_R1)==OBJ+0x44
    removals.append(params.index(receiver)+1)
   elif a in [DELETE_ARRAY,DELETE]:
    if receiver in allocations:
     label=allocations[receiver];events.append([2,label,*refs()]);del allocations[receiver]
     if label==0:
      assert a==DELETE and variant==0 and lr==0x6e7fc
      object_delete_instruction=lr-4
    else:assert a==DELETE_ARRAY and receiver==curves-8
   elif a==BITMAP:
    assert receiver==DATA+0x6000
    events.extend([[3,0,*refs()],[2,10,*refs()]]);del allocations[receiver]
   elif a==0x11f77c:
    assert receiver==OBJ+0x11c;before_shared=refs()
   elif a==0x6f534:assert receiver==OBJ+0x100
   elif a==0x6f3cc:assert receiver==OBJ+0x74
   elif a==0xfb15c:assert receiver==OBJ
   uc.reg_write(UC_ARM_REG_PC,lr);return
  assert any(b['address']<=a<a+size<=b['address']+b['size'] for b,_ in bodies),(hex(a),size)
 def write(uc,access,a,size,value,user):
  assert STACK<=a<a+size<=SP or OBJ<=a<a+size<=OBJ+0x200 or curves<=a<a+size<=curves+40*count or any(p+0x34==a and size==4 for p in images),(hex(a),size)
  if not STACK<=a<SP:writes.append([a,size,value])
 u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
 u.reg_write(UC_ARM_REG_SP,SP);u.reg_write(UC_ARM_REG_LR,STOP);u.reg_write(UC_ARM_REG_R0,OBJ)
 u.emu_start(bodies[variant][0]['address'],STOP,count=10000);assert u.reg_read(UC_ARM_REG_PC)==STOP
 assert refs()==[0,0,0] and (object_delete_instruction is not None)==(variant==0)
 return dict(input=[variant,count,pattern,mask,constructed],removals=removals,source_lifetime_events=events,before_shared_release=before_shared,writes=writes,calls=calls,object_delete_instruction=object_delete_instruction)
def generate():
 bodies=verified();cases=[]
 for variant in range(3):
  for count in [0,1,3]:
   for pattern in range(4):
    for mask in [0,1,2,4,7]:
     for constructed in [0,1]:cases.append(execute(bodies,variant,count,pattern,mask,constructed))
 return dict(elf_sha256=SHA,elf=ELF,bitmap_vtable=bitmap_vtable(),ranges=[b for b,_ in bodies],cases=cases,boundary='Original app target+existing helper instructions only; strict PC/write guards. Core ParamList, vector, Control, Bitmap deleting destructor and allocators are explicitly intercepted boundary observations, not Core binary executions. Native inline shared-image use counts observed. Native D0 actual _ZdlPv callsite must execute; no appended delete event. Host real providers independently execute lifecycle effects. EH paths static only.')
if __name__=='__main__':
 j=generate()
 if '--generate' in sys.argv:(ROOT/OUT).parent.mkdir(parents=True,exist_ok=True);(ROOT/OUT).write_text(json.dumps(j,indent=2)+'\n')
 else:assert j==json.loads((ROOT/OUT).read_text())
 print(len(j['cases']),'independent original ARM lifecycle executions; actual D0 delete call and each D1/D2 range verified')
