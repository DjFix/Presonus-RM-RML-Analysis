"""Original FXPage and complete non-Core float helper closure execution.
The sole Core getter boundary consumes separate actual pinned provider runs."""
import hashlib,json,pathlib,struct,subprocess
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ROOT=pathlib.Path(__file__).resolve().parents[4]
TASK='rolling10_next100_fxpage_prepare'
PACKET='temp/recovery-work/rolling10x10-20261114/prepared06/packets/'+TASK
BINDING='temp/recovery-work/rolling10x10-20261114/READ_INPUTS-prepared06-rolling10_presets.json'
EVIDENCE='temp/recovery-work/rolling10x10-20261114/selection/next100/numeric-state-methods01/native/'+TASK+'.json'
SNAPSHOT=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared06/snapshot')
def sha(b):return hashlib.sha256(b).hexdigest()
def seeds():
 values=[0,0x80000000,1,0x80000001,0x3f000000,0x3f800000,0x40000000,0xbf800000,0xc0000000,0x7f7fffff,0xff7fffff]
 bounds=[(0,0x3f800000),(0xbf800000,0x3f800000),(0x3f800000,0x3f800000),(0x40000000,0xc0000000),(0xc0000000,0xbf800000),(0,0x80000000),(0xff7fffff,0x7f7fffff)]
 return [dict(present=p,value=v,lower=l,upper=h,initial=i) for p in [0,1] for v in values for l,h in bounds for i in [0,1,165]]
def payload(inputs):return ''.join(' '.join(str(s[k]) for k in ['present','value','lower','upper','initial'])+'\n' for s in inputs)
def generate(exe):
 evidence=SNAPSHOT/EVIDENCE;assert sha(evidence.read_bytes())=='3fe4803403f85a83d9cb7b4118a1fa81244416418979da20e09e3efa0be61f57';d=json.loads(evidence.read_text());t=d['target']
 inputs=seeds();r=subprocess.run([str(pathlib.Path(exe).resolve()),'providers'],input=payload(inputs),text=True,capture_output=True,check=True);provider=list(map(int,r.stdout.split()));assert len(provider)==len(inputs)
 elf=pathlib.Path(json.loads((ROOT/BINDING).read_text())['rootfs/RML16AI_Rack_13731/home/root/mixer']['frozen_read_path']);blob=elf.read_bytes();assert sha(blob)==t['original_elf_sha256'];ranges=[];bodies=[]
 with elf.open('rb') as f:
  e=ELFFile(f);table=e.get_section_by_name('.symtab')
  for name,bound in [(t['mangled'],d['verified_body'])]+[(h['identity']['mangled'],h['body']) for h in d['original_nonCore_helpers'].values()]:
   symbol=table.get_symbol_by_name(name)[0];s=e.get_section(symbol['st_shndx']);a=symbol['st_value'];n=symbol['st_size'];off=s['sh_offset']+a-s['sh_addr'];code=blob[off:off+n]
   assert (a,n,off,sha(code))==(bound['address'],bound['size'],bound['file_offset'],bound['bytes_sha256'])
   ranges.append(dict(mangled=name,address=a,size=n,file_offset=off,section=s.name,sha256=sha(code)));bodies.append((a,code))
  vt=d['numeric_vtable'];vbytes=blob[vt['file_offset']:vt['file_offset']+vt['size']];assert sha(vbytes)==vt['sha256'];assert struct.unpack_from('<I',vbytes,8+17*4)[0]==vt['slots']['17']
 cases=[]
 for seed,observed in zip(inputs,provider):
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);mapped=set();getter=d['numeric_vtable']['slots']['17']
  def maprange(a,n):
   for page in range(a&~4095,(a+n+4095)&~4095,4096):
    if page not in mapped:u.mem_map(page,4096);mapped.add(page)
  for a,b in bodies:maprange(a,len(b));u.mem_write(a,b)
  maprange(getter,4);maprange(vt['address'],vt['size']);u.mem_write(vt['address'],vbytes)
  obj=0x1000000;numeric=obj+0x1000;stop=obj+0xf000;stack=0x9000000;maprange(obj,0x10000);maprange(stack,0x10000)
  def word(a,v):u.mem_write(a,struct.pack('<I',v))
  u.mem_write(obj,b'\xa5'*0x200);u.mem_write(obj+5,bytes([seed['initial']]));word(obj+0x11c,numeric if seed['present'] else 0);word(obj+0x120,seed['lower']);word(obj+0x124,seed['upper']);word(numeric,vt['address']+8)
  before=bytes(u.mem_read(obj,0x200));pcs=[];calls=[];writes=[];stack_writes=[]
  def code(uc,pc,size,_):
   if pc==stop:uc.emu_stop();return
   if pc==getter:
    assert seed['present'] and uc.reg_read(UC_ARM_REG_R0)==numeric
    calls.append(dict(identity='_ZNK4Core8Portable12NumericParam8getValueEv',slot=17,return_bits=observed));uc.reg_write(UC_ARM_REG_R0,observed);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
   assert any(a<=pc<a+len(b) for a,b in bodies),hex(pc);pcs.append(pc)
  def write(uc,access,a,n,v,_):
   if stack<=a and a+n<=stack+0x10000:stack_writes.append([a,n,v])
   else:
    assert a==obj+5 and n==1,(hex(a),n);writes.append([5,n,v])
  u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
  for reg,value in [(UC_ARM_REG_R0,obj),(UC_ARM_REG_SP,stack+0x8000),(UC_ARM_REG_LR,stop)]:u.reg_write(reg,value)
  u.emu_start(t['address'],stop+4,count=512);assert u.reg_read(UC_ARM_REG_PC)==stop
  after=bytes(u.mem_read(obj,0x200));assert before[:5]==after[:5] and before[6:]==after[6:];assert len(calls)==seed['present'];assert len(writes)==1 and after[5] in [0,1]
  cases.append(dict(input=seed,provider_return_bits=observed,result=after[5],executed_pcs=pcs,getter_calls=calls,application_writes=writes,stack_writes=stack_writes,other_state_unchanged=True))
 return dict(task_id=TASK,elf_sha256=t['original_elf_sha256'],ranges=ranges,numeric_vtable=dict(address=vt['address'],size=vt['size'],sha256=vt['sha256'],getter= getter),provider_observations=provider,cases=cases,limitations='Finite float values/bounds only, including signed zeros, subnormals, maximum finite extremes and reversed bounds. Original target and every non-Core comparison helper alias range verified separately and executed without helper stubs. Original NumericParam body never loaded/executed: typed slot17 boundary returns independently executed actual pinned provider observations. No NaN/infinity, unknown subclass overrides, original layout/lifecycle/return declaration/ARM ABI or hardware claim.')
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--exe',required=True);p.add_argument('--out',required=True);a=p.parse_args();pathlib.Path(a.out).write_text(json.dumps(generate(a.exe),indent=2)+'\n')
