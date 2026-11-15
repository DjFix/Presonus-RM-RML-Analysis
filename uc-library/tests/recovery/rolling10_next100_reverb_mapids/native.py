"""Independent execution of the exact sealed non-Core local switch."""
import hashlib,json,pathlib,random,struct
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ROOT=pathlib.Path(__file__).resolve().parents[4]
TASK='rolling10_next100_reverb_mapids'
PACKET='temp/recovery-work/rolling10x10-20261114/prepared06/packets/'+TASK
BINDING='temp/recovery-work/rolling10x10-20261114/READ_INPUTS-prepared06-rolling10_presets.json'
def sha(b):return hashlib.sha256(b).hexdigest()
def generate():
 t=json.loads((ROOT/PACKET/'request.json').read_text())['targets'][0]
 elf=pathlib.Path(json.loads((ROOT/BINDING).read_text())['rootfs/RML16AI_Rack_13731/home/root/mixer']['frozen_read_path']);blob=elf.read_bytes();assert sha(blob)==t['original_elf_sha256']
 with elf.open('rb') as f:
  e=ELFFile(f);s=e.get_section_by_name('.symtab').get_symbol_by_name(t['mangled'])[0];sec=e.get_section(s['st_shndx']);a=s['st_value'];n=s['st_size'];off=sec['sh_offset']+a-sec['sh_addr'];body=blob[off:off+n]
  assert (a,n,s['st_shndx'])==(t['address'],t['size'],t['section']);assert sha(body)=='89090b287ea76b92eaeae9f75cb667bdd2106d1b341b23fa5ab6447403e15e2a'
 table=struct.unpack_from('<15I',body,0x1c);assert all(a<=p<a+n and p%4==0 for p in table)
 seeds=list(range(-32,65))+[-2147483648,-2147483647,-2147483646,2147483645,2147483646,2147483647]
 rng=random.Random(13731);seeds+= [rng.randint(-2147483648,2147483647) for _ in range(256)]
 cases=[]
 for receiver in [0x1000000,0x1001000]:
  for selector in seeds:
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(a&~4095,4096);u.mem_write(a,body);u.mem_map(0x1000000,0x10000);u.mem_map(0x9000000,0x10000)
   stop=0x100f000;pcs=[];writes=[];before=bytes(u.mem_read(receiver,256))
   def code(uc,pc,size,_):
    if pc==stop:uc.emu_stop();return
    assert a<=pc<a+n,hex(pc);pcs.append(pc)
   def write(uc,access,p,size,v,_):
    assert 0x9000000<=p and p+size<=0x9010000,(hex(p),size);writes.append([p,size,v])
   u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
   for r,v in [(UC_ARM_REG_R0,receiver),(UC_ARM_REG_R1,selector&0xffffffff),(UC_ARM_REG_SP,0x9008000),(UC_ARM_REG_LR,stop)]:u.reg_write(r,v)
   u.emu_start(a,stop+4,count=64);assert u.reg_read(UC_ARM_REG_PC)==stop;assert bytes(u.mem_read(receiver,256))==before
   v=u.reg_read(UC_ARM_REG_R0);cases.append(dict(receiver=receiver,selector=selector,result=v if v<2**31 else v-2**32,pcs=pcs,stack_writes=writes,object_unchanged=True,external_calls=[]))
 return dict(task_id=TASK,elf_sha256=t['original_elf_sha256'],range=dict(mangled=t['mangled'],address=a,size=n,section=sec.name,section_index=s['st_shndx'],file_offset=off,sha256=sha(body)),jump_table=dict(address=a+0x1c,size=60,sha256=sha(body[0x1c:0x58]),destinations=list(table)),cases=cases,limitations='Closed local original ARM body only; no Core or external execution. Finite default samples plus structural unsigned guard/table partition evidence; no exhaustive execution of 2^32 inputs, original return declaration/layout/ABI/hardware claim.')
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();pathlib.Path(a.out).write_text(json.dumps(generate(),indent=2)+'\n')
