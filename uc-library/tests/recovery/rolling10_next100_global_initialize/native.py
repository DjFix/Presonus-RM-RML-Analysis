#!/usr/bin/env python3
"""Execute exact original guard; its accepted app tail provider runs as C++."""
import argparse,hashlib,io,itertools,json,struct,subprocess
from pathlib import Path
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import *
from unicorn.arm_const import *
T=Path(__file__).resolve().parent;R=T.parents[3];TASK=T.name;BASE=R/'temp/recovery-work/rolling10x10-20261114';PACKET=BASE/'prepared-remaining14-phasea-proposed01/packets'/TASK
READ=BASE/'READ_INPUTS-prepared-remaining14-phasea-proposed01-rolling10_fx.json'
def sha(b):return hashlib.sha256(b).hexdigest()
def inputs():
 source=[0,0x80000000,0x3f800000,0x3fffffff,0x40000000,0x40000001,0x40800000,0xc0000000,0x7f800000,0xff800000,0x7fc12345,0x7fa12345]
 for mask,alias,s,d,n in itertools.product(range(4),[0,1],source,[0,0x3f000000,0x3f800000,0x7fc12345],[0,1,3]):yield [mask,alias,s,d,n]
def generate(exe):
 target=json.loads((PACKET/'request.json').read_text())['targets'][0];raw=Path(json.loads(READ.read_text())['rootfs/RML16AI_Rack_13731/home/root/mixer']['frozen_read_path']).read_bytes();assert sha(raw)==target['original_elf_sha256'];e=ELFFile(io.BytesIO(raw));symbols=list(e.get_section_by_name('.symtab').iter_symbols());s=next(s for s in symbols if s.name==target['mangled']);sec=e.get_section(s['st_shndx']);off=sec['sh_offset']+s['st_value']-sec['sh_addr'];body=raw[off:off+s['st_size']];assert(s['st_value'],s['st_size'],s['st_shndx'],sha(body))==(target['address'],44,12,'e7a5c5d8094ccb758af685620efc9aaa57ac02a2cbb42c055b5fd9b70c49023d');provider=next(s for s in symbols if s.name=='_ZN8Presonus5Mixer15GlobalComponent13updateHighDefEv');assert(provider['st_value'],provider['st_size'])==(296288,100)
 rows=[];provider_inputs=[]
 for idx,case in enumerate(inputs()):
  mask,alias,sbits,dbits,repeats=case;u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  for addr in [s['st_value']&~4095,0x2000000,0x3000000,0x4000000]:u.mem_map(addr,4096)
  u.mem_write(s['st_value'],body);u.mem_write(0x2000000,b'\xa5'*4096);self=0x2000100+(idx%2)*0x200;source=0x2000800;destination=source if alias else 0x2000900;sp=0x3000800;stop=0x4000000
  u.mem_write(self+0x8c,struct.pack('<I',source if mask&1 else 0));u.mem_write(self+0x90,struct.pack('<I',destination if mask&2 else 0));initial=bytes(u.mem_read(0x2000000,4096));pcs=[];writes=[];tails=[]
  def code(uc,pc,n,d):
   if pc==stop:uc.emu_stop();return
   if pc==provider['st_value']:
    assert uc.reg_read(UC_ARM_REG_R0)==self and uc.reg_read(UC_ARM_REG_SP)==sp and uc.reg_read(UC_ARM_REG_LR)==stop;tails.append(dict(original_mangled=provider.name,address=pc,receiver=self,stack_restored_before_tail=True,caller_lr_preserved=True));uc.reg_write(UC_ARM_REG_PC,stop);return
   assert s['st_value']<=pc<s['st_value']+s['st_size'];pcs.append(pc)
  def write(uc,access,a,n,v,d):
   assert sp-16<=a<a+n<=sp;writes.append([a,n,v&((1<<(8*n))-1)])
  u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
  for iteration in range(repeats):
   u.reg_write(UC_ARM_REG_CPSR,0x10);u.reg_write(UC_ARM_REG_R0,self);u.reg_write(UC_ARM_REG_SP,sp);u.reg_write(UC_ARM_REG_LR,stop);u.emu_start(s['st_value'],stop+4,count=32);assert u.reg_read(UC_ARM_REG_PC)==stop and u.reg_read(UC_ARM_REG_SP)==sp
  assert bytes(u.mem_read(0x2000000,4096))==initial
  rows.append(dict(input=case,tail_count=len(tails),tail_observations=tails,pcs=pcs,stack_writes=writes,other_memory_unchanged=True))
  provider_inputs.append([mask,alias,sbits,dbits,len(tails)])
 # Accepted updateHighDef provider executes only as many times as observed by
 # original ARM control flow. No new initializer implementation is invoked.
 payload=''.join(' '.join(map(str,c))+'\n' for c in provider_inputs);p=subprocess.run([str(exe),'--provider'],input=payload,text=True,capture_output=True,check=True,cwd=R);out=p.stdout.splitlines();assert len(out)==len(rows)
 for row,result in zip(rows,out):row['accepted_provider_observation']=list(map(int,result.split()))
 return dict(task_id=TASK,elf_sha256=sha(raw),mangled=target['mangled'],range=dict(address=s['st_value'],size=44,section=sec.name,section_index=s['st_shndx'],file_offset=off,sha256=sha(body)),accepted_tail_provider=dict(mangled=provider.name,address=provider['st_value'],size=provider['st_size'],original_body_executed=False,scope='Existing accepted source implementation and actual CCL NumericParam getter/setter/observer/controller operations; not new initializer expectations or an ARM ABI claim.'),cases=rows,producer_sha256=sha(Path(__file__).read_bytes()),unicorn_version=unicorn.__version__,limitations='Native caller executes exact44B instructions only. No native Core or already-source-provided app body reconstructed/executed; captured tail counts drive independent actual provider executions. Initial parameter bit canonicalization/NaN notifications are actual CCL observations, not numeric equality expectations. No original static return/layout/ownership/ARM/hardware credit.')
def main():
 p=argparse.ArgumentParser();p.add_argument('--exe',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(generate(a.exe.resolve()),indent=2)+'\n')
if __name__=='__main__':main()
