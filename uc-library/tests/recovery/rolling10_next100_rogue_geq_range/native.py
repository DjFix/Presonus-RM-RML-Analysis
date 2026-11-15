#!/usr/bin/env python3
import argparse,hashlib,io,itertools,json,struct,subprocess
from pathlib import Path
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import *
from unicorn.arm_const import *
T=Path(__file__).resolve().parent;R=T.parents[3];TASK=T.name;PACKET=R/'temp/recovery-work/rolling10x10-20261114/prepared06/packets'/TASK
READ=R/'temp/recovery-work/rolling10x10-20261114/READ_INPUTS-prepared06-rolling10_fx.json'
def sha(b):return hashlib.sha256(b).hexdigest()
def inputs():
 vals=[-2147483648.,-16777216.,-16.75,-1.75,-.5,-0.,0.,.5,1.,3.,4.,14.99,15.,15.99,16.,26.,27.,31.5,2147483520.]
 for value,offset,count in itertools.product(vals,[-2147483648,-1,0,3,15,27,2147483647],[0,1,4,15,16,32]):
  yield [struct.unpack('<I',struct.pack('<f',value))[0],1,offset,count]
 for offset,count in itertools.product([-2147483648,-1,0,3,15,27,2147483647],[0,1,4,15,16,32]):yield [0,0,offset,count]
def generate(exe):
 target=json.loads((PACKET/'request.json').read_text())['targets'][0];raw=Path(json.loads(READ.read_text())['rootfs/RML16AI_Rack_13731/home/root/mixer']['frozen_read_path']).read_bytes();assert sha(raw)==target['original_elf_sha256'];elf=ELFFile(io.BytesIO(raw));syms=list(elf.get_section_by_name('.symtab').iter_symbols())
 def get(a,n):
  s=next(s for s in elf.iter_sections() if s['sh_type']!='SHT_NOBITS' and s['sh_addr']<=a<a+n<=s['sh_addr']+s['sh_size']);o=s['sh_offset']+a-s['sh_addr'];return raw[o:o+n],s.name,o
 start,size=target['address'],target['size'];body,section,offset=get(start,size);sym=next(s for s in syms if s.name==target['mangled']);assert(sym['st_value'],sym['st_size'],sym['st_shndx'])==(start,size,target['section'])
 helpers=[]
 for name in ['__fixsfsi','__aeabi_f2iz']:
  s=next(s for s in syms if s.name==name);b,sec,off=get(s['st_value'],s['st_size']);assert sha(b)=='73908d204e4625c30fc21dff9a2f817e26c53d161164a032bd229a9dcdd6edee';helpers.append(dict(mangled=name,address=s['st_value'],size=s['st_size'],section=sec,file_offset=off,sha256=sha(b)))
 helper=helpers[0];helperbody=get(helper['address'],helper['size'])[0]
 cases=list(inputs());p=subprocess.run([str(exe),'--provider'],input=''.join(' '.join(map(str,c))+'\n' for c in cases),text=True,capture_output=True,check=True,cwd=R);provider=[list(map(int,x.split())) for x in p.stdout.splitlines()];assert len(provider)==len(cases)
 rows=[]
 for case,observed in zip(cases,provider):
  bits,present,old,count=case;actualbits,actualcount=observed;assert actualcount==count
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  for a in [start&~4095,helper['address']&~4095,0x5000000,0x2000000,0x3000000,0x4000000]:u.mem_map(a,4096)
  u.mem_write(start,body);u.mem_write(helper['address'],helperbody);u.mem_write(0x2000000,b'\xa5'*4096)
  self=0x2000100;numeric=0x2000400;mixer=0x2000600;table=0x2000a00;getter=0x5000000;sp=0x3000800;stop=0x4000000
  def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
  w(self+0x17c,numeric if present else 0);w(self+0x8c,mixer);w(self+0x16c,old);w(mixer+0x138,actualcount);w(numeric,table);w(table+0x44,getter);initial=bytes(u.mem_read(0x2000000,4096));pcs=[];writes=[];calls=[]
  def code(uc,pc,n,d):
   if pc==stop:uc.emu_stop();return
   if pc==getter:
    assert uc.reg_read(UC_ARM_REG_R0)==numeric;calls.append(dict(boundary='original Numeric slot17 -> actual pinned Parameter::getValue virtual call',native_receiver=numeric,observed_bits=actualbits));uc.reg_write(UC_ARM_REG_R0,actualbits);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
   assert start<=pc<start+size or helper['address']<=pc<helper['address']+helper['size'],hex(pc);pcs.append(pc)
  def write(uc,access,a,n,v,d):
   assert sp-24<=a<a+n<=sp or (a==self+0x16c and n==4),(a,n);writes.append([a,n,v&((1<<(8*n))-1)])
  u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write);u.reg_write(UC_ARM_REG_CPSR,0x10);u.reg_write(UC_ARM_REG_R0,self);u.reg_write(UC_ARM_REG_SP,sp);u.reg_write(UC_ARM_REG_LR,stop);u.emu_start(start,stop+4,count=100);assert u.reg_read(UC_ARM_REG_PC)==stop and u.reg_read(UC_ARM_REG_SP)==sp
  result=u.reg_read(UC_ARM_REG_R0);newoff=struct.unpack('<i',u.mem_read(self+0x16c,4))[0];after=bytes(u.mem_read(0x2000000,4096));expected=bytearray(initial);expected[self+0x16c-0x2000000:self+0x170-0x2000000]=after[self+0x16c-0x2000000:self+0x170-0x2000000];assert after==bytes(expected);assert len(calls)==present
  rows.append(dict(input=case,expected=[result,newoff],provider_observed=observed,provider_calls=calls,pcs=pcs,writes=writes,stack_restored=True,other_memory_unchanged=True))
 return dict(task_id=TASK,elf_sha256=sha(raw),mangled=target['mangled'],address=start,size=size,section=section,file_offset=offset,range_sha256=sha(body),helper_alias_ranges=helpers,cases=rows,producer_sha256=sha(Path(__file__).read_bytes()),unicorn_version=unicorn.__version__,provider_scope='Actual borrowed NumericParam getter and actual authoritative MixerComponentBase inputChannels vector count; only Core boundary modeled. Full original non-Core float conversion instructions execute with separate alias range checks. Finite int32 representable floats only.')
def main():
 p=argparse.ArgumentParser();p.add_argument('--exe',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(generate(a.exe.resolve()),indent=2)+'\n')
if __name__=='__main__':main()
