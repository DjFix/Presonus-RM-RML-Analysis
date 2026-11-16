"""Original outer destructor execution; named FrontPanel provider boundary.
No Core binary execution, allocator implementation or hardware access.
"""
from pathlib import Path
import hashlib,json,struct,subprocess
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
R=Path(__file__).resolve().parents[4]
CANON=Path('/home/rs/projects/opencs/ai-line-analysis')
PACKETS=CANON/'temp/recovery-work/reconstruction10x10-20261116/prepared-main/packets'
ELF=CANON/'rootfs/RML16AI_Rack_13731/home/root/mixer'
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
def digest(b):return hashlib.sha256(b).hexdigest()
def generate(task,exe):
 raw=ELF.read_bytes();assert digest(raw)==SHA
 req=json.loads((PACKETS/task/'request.json').read_text());target=req['targets'][0]
 with ELF.open('rb') as f:
  ef=ELFFile(f);sym=next(s for s in ef.get_section_by_name('.symtab').iter_symbols() if s.name==target['mangled'])
  sec=ef.get_section(sym['st_shndx']);offset=sec['sh_offset']+sym['st_value']-sec['sh_addr']
  assert (sym['st_value'],sym['st_size'],sym['st_shndx'])==(target['address'],target['size'],target['section'])
  bound=json.loads((PACKETS/task/'native-context.json').read_text())
  body=next(b for b in bound['bodies'].values() if b['address']==target['address'])
  assert offset==body['file_offset'] and digest(raw[offset:offset+sym['st_size']])==body['bytes_sha256']
  loads=[(s['p_vaddr'],s.data()) for s in ef.iter_segments() if s['p_type']=='PT_LOAD']
  # Resolve native PLT delete by actual relocation, not a convenient address label.
  plt=ef.get_section_by_name('.plt');rel=ef.get_section_by_name('.rel.plt');dyn=ef.get_section(rel['sh_link']);idx=(0xac10-plt['sh_addr']-20)//12
  assert dyn.get_symbol(list(rel.iter_relocations())[idx]['r_info_sym']).name=='_ZdlPv'
 expansion=CANON/'temp/recovery-work/reconstruction10x10-20261116/expansions/bound-20261116T055348/g08-frontpanel-dtor/native-context.json'
 base=next(b for b in json.loads(expansion.read_text())['bodies'].values() if b['address']==0x68fc8)
 assert digest(raw[base['file_offset']:base['file_offset']+base['size']])==base['bytes_sha256']
 cases=[];deleting='D0Ev' in target['mangled'];kind='rogue' if 'Rogue' in target['mangled'] else 'fat'
 for populated in [0,1,8]:
  provider=json.loads(subprocess.check_output([str(exe),'base','D1',str(populated)],cwd=R,text=True))
  assert provider['released']==provider['owned_allocations'] and provider['live']==1 and provider['self_deallocated']==0
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x800000)
  for a,data in loads:u.mem_write(a,data)
  obj=0x1000000;stack=0x1100000;stop=0x1200000
  for a,size in [(obj,0x1000),(stack,0x10000),(stop,0x1000)]:u.mem_map(a,size)
  u.mem_write(obj,bytes([0xa5])*0x400);trace=[];writes=[];pcs=[];live=True
  def hook(uc,a,n,data):
   nonlocal live
   if a==stop:uc.emu_stop();return
   x=uc.reg_read(UC_ARM_REG_R0)
   if a==0x68fc8:
    assert x==obj;trace.append(['FrontPanel_destructor',0])
   if a in [0x8c630,0x1228b0,0x6a054,0x5292c]:
    assert x in [obj+0x198,obj+0x144,obj+0x130,obj+0x11c,obj]
    trace.append([{0x8c630:'DelayTimer_provider',0x1228b0:'Attributes_provider',0x6a054:'Vector_provider',0x5292c:'PanelComponent_provider'}[a],x-obj]);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
   if a==0xac10:
    assert x==obj and live;live=False;trace.append(['operator_delete',0]);uc.mem_unmap(obj,0x1000);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
   assert target['address']<=a<a+n<=target['address']+target['size'] or base['address']<=a<a+n<=base['address']+base['size'],hex(a)
   pcs.append(a)
  def write(uc,access,a,n,value,data):
   assert obj<=a<a+n<=obj+0x400 or stack<=a<a+n<=stack+0x10000
   if obj<=a<obj+0x400:writes.append([a-obj,n,value])
  u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
  u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_SP,stack+0xff00);u.reg_write(UC_ARM_REG_LR,stop)
  u.emu_start(target['address'],stop,count=1000)
  assert u.reg_read(UC_ARM_REG_PC)==stop and u.reg_read(UC_ARM_REG_R0)==obj
  assert len(writes)==14 and sorted(w[0] for w in writes)==sorted([0,4,0x84,0xf0,0xf4,0xf8,0xfc]*2)
  assert trace==[['FrontPanel_destructor',0],['DelayTimer_provider',0x198],['Attributes_provider',0x144],['Vector_provider',0x130],['Vector_provider',0x11c],['PanelComponent_provider',0]]+([['operator_delete',0]] if deleting else []) and live!=deleting
  cases.append({'populated':populated,'kind':kind,'variant':'D0' if deleting else 'D1','native_calls':trace,'native_writes':writes,'native_self_deallocated':not live,'pc_sha256':digest(b''.join(struct.pack('<I',a) for a in pcs)),'instructions':len(pcs),'provider':provider,'expected':{'owned_allocations':provider['owned_allocations'],'released':provider['released'],'live':0 if deleting else 1,'self_deallocated':int(deleting),'core_released':provider['core_released'],'core_live':0,'borrowed':42}})
 return {'version':1,'task':task,'elf_sha256':SHA,'range':dict(target,file_offset=offset,section_name=sec.name,bytes_sha256=digest(raw[offset:offset+target['size']])),'base_range':base,'cases':cases,'domain':'Valid owned tagged receivers, empty/one/eight borrowed vector slots; actual native outer vptr writes and base/delete calls. Original FrontPanel destructor normal path also executes; its DelayTimer, Attributes, two Vector and Panel boundaries are named stubs. Actual canonical base and CCL cleanup separately executed in base provider mode. No original allocator implementation, native provider bodies, original layout/multiple inheritance, EH, hardware or ABI claim.'}
