"""Exact app-range execution only; CCL firmware is never executed.
The two intercepted calls use actual current filename/cache and pinned POSIX
provider observations, independently of isSlotEmpty's reconstructed body.
"""
import hashlib,json,pathlib,subprocess,tempfile
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_LR,UC_ARM_REG_PC,UC_ARM_REG_SP
ROOT=pathlib.Path(__file__).resolve().parents[5]
BASE=ROOT/'temp/recovery-work/frontier-scale02/frontier02_w06'
ELF=ROOT/'rootfs/RML16AI_Rack_13731/home/root/mixer'
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
CASES=[{'id':'missing','slot':0,'name':'Missing','category':'','kind':'missing'},
 {'id':'regular','slot':1,'name':'Regular','category':'Vocal','kind':'file'},
 {'id':'directory','slot':2,'name':'Directory','category':'','kind':'dir'},
 {'id':'symlink','slot':3,'name':'Link','category':'','kind':'link'},
 {'id':'dangling','slot':0,'name':'Dangling','category':'','kind':'dangling'},
 {'id':'trim','slot':1,'name':'  Spaced  ','category':'  Vocal  ','kind':'file'},
 {'id':'empty-marker','slot':2,'name':'','category':'','kind':'missing'}]
def invoke(exe,*args):return subprocess.check_output([str(exe),*map(str,args)],text=True).strip()
def prepare(exe,run,c):
 folder=run/c['id'];folder.mkdir()
 args=[folder,c['slot'],c['name'],c['category']]
 path=pathlib.Path(invoke(exe,'path',*args))
 if c['kind']=='file':path.write_text('bounded provider fixture\n')
 if c['kind']=='dir':path.mkdir()
 if c['kind']=='link':
  target=folder/'target';target.write_text('target\n');path.symlink_to(target)
 if c['kind']=='dangling':path.symlink_to(folder/'absent-target')
 return args,str(path),int(invoke(exe,'provider',path))
def native(code,path,exists,slot):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x80000,0xb0000);u.mem_write(0x83e18,code)
 u.mem_map(0x200000,0x10000);u.mem_map(0x300000,0x1000)
 u.reg_write(UC_ARM_REG_SP,0x20f000);u.reg_write(UC_ARM_REG_R0,0x200100)
 u.reg_write(UC_ARM_REG_R1,slot);u.reg_write(UC_ARM_REG_LR,0x300000)
 trace=[];pcs=[];writes=[]
 def hook(uc,pc,size,data):
  if pc==0x300000:uc.emu_stop();return
  if pc==0x83de0:
   assert uc.reg_read(UC_ARM_REG_R1)==0x200100 and uc.reg_read(UC_ARM_REG_R2)==slot
   uc.mem_write(uc.reg_read(UC_ARM_REG_R0),path.encode()+b'\0');trace.append('getFileNameForSlot')
   uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
  if pc==0x12784c:
   ptr=uc.reg_read(UC_ARM_REG_R0);observed=bytes(uc.mem_read(ptr,len(path)+1))
   assert observed==path.encode()+b'\0';trace.append('FileUtils::fileExists')
   uc.reg_write(UC_ARM_REG_R0,exists);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
  assert 0x83e18<=pc<0x83e60,hex(pc);pcs.append(pc-0x83e18)
 def write(uc,access,address,size,value,data):
  assert 0x20e000<=address<0x20f000
  writes.append({'sp_relative':address-0x20f000,'size':size})
 u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
 u.emu_start(0x83e18,0x300004,count=100)
 assert u.reg_read(UC_ARM_REG_PC)==0x300000
 return {'result':u.reg_read(UC_ARM_REG_R0),'calls':trace,'instruction_offsets':pcs,'stack_writes':writes}
def observe(exe):
 raw=ELF.read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
 with ELF.open('rb') as f:
  elf=ELFFile(f);section=elf.get_section(12)
  offset=section['sh_offset']+0x83e18-section['sh_addr']
  symbol=[s for s in elf.get_section_by_name('.symtab').iter_symbols() if s.name=='_ZNK8Presonus5Panel15PresetComponent11isSlotEmptyEj']
  assert len(symbol)==1 and symbol[0]['st_value']==0x83e18 and symbol[0]['st_size']==72
 assert offset==0x7be18
 code=raw[offset:offset+72];assert hashlib.sha256(code).hexdigest()=='7c3d80e913ee73516b529d3a9b2af89bcd10ac1943d24797c20fd3cac73a7b96'
 run=pathlib.Path(tempfile.mkdtemp(prefix='oracle-',dir=BASE));results=[]
 for c in CASES:
  args,path,exists=prepare(exe,run,c)
  results.append({**c,'provider_exists':exists,'filename_basename':pathlib.Path(path).name,'native':native(code,path,exists,c['slot'])})
 results.append({'id':'empty-boundary-only','native':native(code,'',0,0),'exclusion':'not reachable through current nonempty cache filename model'})
 out={'elf_sha256':SHA,'section':12,'file_offset':offset,'size':72,'range_sha256':hashlib.sha256(code).hexdigest(),'cases':results}
 (run/'observations.json').write_text(json.dumps(out,indent=2)+'\n')
 return out
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures');p.add_argument('--generate',action='store_true');a=p.parse_args()
 out=observe(a.executable)
 if a.generate:pathlib.Path(a.fixtures).write_text(json.dumps(out,indent=2)+'\n')
 elif a.fixtures:assert out==json.loads(pathlib.Path(a.fixtures).read_text())
 print('native/provider cases',len(out['cases']))
