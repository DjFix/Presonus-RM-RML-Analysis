"""Independent exact original Scenes constructor variant, no base/Core firmware.
The base boundary is observed from original args and replayed with actual provided
PresetComponent. Construction comparison ends before actual host cleanup.
"""
import hashlib,json,pathlib,struct,subprocess
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ROOT=pathlib.Path(__file__).resolve().parents[4]
TASK=pathlib.Path(__file__).parent.name
BASE=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared-next-flow01')
def sha(b):return hashlib.sha256(b).hexdigest()
def generate(exe):
 req=json.loads((BASE/'packets'/TASK/'request.json').read_text());t=req['targets'][0];ev=BASE/'snapshot/temp/recovery-work/rolling10x10-20261114/selection/next100/scenes-construction01/native'/ (TASK+'.json');evidence=json.loads(ev.read_text());binding=json.loads((ROOT/'temp/recovery-work/rolling10x10-20261114/READ_INPUTS-prepared-next-flow01-rolling10_presets.json').read_text());elf=pathlib.Path(binding['rootfs/RML16AI_Rack_13731/home/root/mixer']['frozen_read_path']);blob=elf.read_bytes();assert sha(blob)==t['original_elf_sha256']
 with elf.open('rb') as f:
  e=ELFFile(f);syms=e.get_section_by_name('.symtab');sym=syms.get_symbol_by_name(t['mangled'])[0];sec=e.get_section(sym['st_shndx']);off=sec['sh_offset']+sym['st_value']-sec['sh_addr'];body=blob[off:off+100];assert (sym['st_value'],sym['st_size'],sha(body))==(t['address'],100,evidence['verified_body']['bytes_sha256']);base=syms.get_symbol_by_name('_ZN8Presonus5Panel15PresetComponentC2EPKcS3_S3_RNS_5Mixer18MixerComponentBaseE')[0];assert base['st_value']==539492
 strings=[]
 for item in evidence['base_constructor_string_arguments']:
  data=bytes.fromhex(item['bytes_hex']);assert blob[item['file_offset']:item['file_offset']+len(data)]==data and sha(data)==item['sha256'];strings.append(data[:-1].decode())
 cases=[]
 for index in range(24):
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(t['address']&~4095,8192);u.mem_write(t['address'],body);u.mem_map(539492&~4095,4096);obj=0x1000000+index*16;panel=0x2000000+index*32;mixer=0x3000000+index*64;stack=0x9000000;stop=0x100f000;u.mem_map(0x1000000,0x10000);u.mem_map(stack,0x10000);u.mem_write(obj,b'\xa5'*256);calls=[];writes=[];pcs=[]
  def hook(uc,pc,n,_):
   if pc==stop:uc.emu_stop();return
   if pc==539492:
    args=[uc.reg_read(r) for r in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]];mix=struct.unpack('<I',uc.mem_read(uc.reg_read(UC_ARM_REG_SP),4))[0];assert args==[obj,*[x['address'] for x in evidence['base_constructor_string_arguments']]] and mix==mixer;assert bytes(uc.mem_read(obj,256))==b'\xa5'*256;calls.append(dict(target=pc,args=args,mixer=mix,strings=strings,panel_not_stored_yet=True,actual_base_observation=subprocess.run([str(exe),'base',str(index%2),*strings],text=True,capture_output=True,check=True).stdout));uc.reg_write(UC_ARM_REG_R0,obj);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
   assert t['address']<=pc<t['address']+84;pcs.append(pc)
  def write(uc,ac,a,n,v,_):
   if stack<=a and a+n<=stack+0x10000:return
   assert obj<=a and a+n<=obj+256;writes.append([a-obj,n,v])
  u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
  for r,v in [(UC_ARM_REG_R0,obj),(UC_ARM_REG_R1,panel),(UC_ARM_REG_R2,mixer),(UC_ARM_REG_SP,stack+0x8000),(UC_ARM_REG_LR,stop)]:u.reg_write(r,v)
  u.emu_start(t['address'],stop+4,count=128);assert u.reg_read(UC_ARM_REG_PC)==stop and u.reg_read(UC_ARM_REG_R0)==obj and len(calls)==1;assert writes==[[200,4,panel],[4,4,1515432+84],[132,4,1515432+100],[0,4,1515432]]
  cases.append(dict(index=index,base_calls=calls,derived_writes=writes,executed_pcs=pcs,return_this=True))
 # Actual base provider gets only the original observed literal strings. Its
 # output is independently compared with newly reconstructed Scenes, not used
 # to determine native argument expectations.
 providers={}
 for present in [0,1]:
  providers[str(present)]=subprocess.run([str(exe),'base',str(present),*strings],text=True,capture_output=True,check=True).stdout
 return dict(task_id=TASK,elf_sha256=t['original_elf_sha256'],range=dict(address=t['address'],size=100,file_offset=off,section='.text',sha256=sha(body)),literal_arguments=evidence['base_constructor_string_arguments'],cases=cases,providers=providers,limitations='Normal construction; original exact variant executes independently with actual provided base boundary observations. Only borrowed panel association plus base arguments/order are recovered. Native vptr writes recorded, host vptr/layout intentionally differs. Actual cleanup occurs separately after construction observation. No original derived destructor, EH/full virtual interface, ARM ABI or hardware credit.')
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--exe',required=True);p.add_argument('--out',required=True);a=p.parse_args();pathlib.Path(a.out).write_text(json.dumps(generate(pathlib.Path(a.exe).resolve()),indent=2)+'\n')
