ROOT='/home/rs/projects/opencs/ai-line-analysis'
PACKET='/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/compact-10x20-20261113/generated-implementation40/prepared03/packets/compact20_panel_registrars_17'
TAG=False
import json,hashlib,struct,sys
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
p=Path(PACKET); nc=json.loads((p/'native-context.json').read_text()); req=json.loads((p/'request.json').read_text()); t=req['targets'][0]; body=nc['bodies'][nc['roots'][0]]; elfpath=Path(ROOT)/nc['binaries'][t['original_elf_sha256']]['path']; assert hashlib.sha256(elfpath.read_bytes()).hexdigest()==t['original_elf_sha256']
with elfpath.open('rb') as f:
 elf=ELFFile(f); segments=[(s['p_vaddr'],s.data(),s['p_memsz']) for s in elf.iter_segments() if s['p_type']=='PT_LOAD']; section=elf.get_section(int(t['section'])); offset=t['address']-section['sh_addr']+section['sh_offset']; assert offset==body['file_offset']; f.seek(offset); assert hashlib.sha256(f.read(t['size'])).hexdigest()==body['bytes_sha256']
cases=[]
for group in list(range(-8,33))+[-2147483648,2147483647]:
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
 for va,data,ms in segments:
  lo=va&~4095;u.mem_map(lo,((va+ms+4095)&~4095)-lo);u.mem_write(va,data)
 for a,size in [(0x70000000,0x20000),(0x71000000,4096),(0x72000000,4096),(0x73000000,4096)]:u.mem_map(a,size)
 sp=0x70010000;stop=0x72000000;out=0x71000000;receiver=0x73000000;u.mem_write(receiver,bytes([0xa5])*256);u.mem_write(out,struct.pack('<I',0x13579bdf));u.reg_write(UC_ARM_REG_SP,sp);u.reg_write(UC_ARM_REG_LR,stop);u.reg_write(UC_ARM_REG_R0,receiver);u.reg_write(UC_ARM_REG_R1,group&0xffffffff);u.reg_write(UC_ARM_REG_R2,out);trace=[]
 def hook(uc,a,size,data):
  if a==stop:uc.emu_stop();return
  assert t['address']<=a<t['address']+t['size'];trace.append(a)
 u.hook_add(UC_HOOK_CODE,hook);u.emu_start(t['address'],stop,count=200);assert u.reg_read(UC_ARM_REG_PC)==stop;assert u.reg_read(UC_ARM_REG_SP)==sp;assert bytes(u.mem_read(receiver,256))==bytes([0xa5])*256
 value=u.reg_read(UC_ARM_REG_R0);count=struct.unpack('<i',u.mem_read(out,4))[0]
 expected=[int(value!=0),count]+(list(struct.unpack('<'+'i'*count,u.mem_read(value,4*count))) if value else []) if TAG else [value]
 cases.append({'group':group,'expected':expected,'trace':trace,'stack_restored':True,'receiver_unchanged':True})
result={'version':1,'target':t,'elf_path':str(elfpath),'range':body,'native_producer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'cases':cases,'domain':'Every valid group, -8..32, INT_MIN/MAX; exact original ARM execution with private memory only, no providers/hardware; outputs, receiver bytes and restored stack.'}
Path(sys.argv[1]).write_text(json.dumps(result,indent=2)+'\n')
