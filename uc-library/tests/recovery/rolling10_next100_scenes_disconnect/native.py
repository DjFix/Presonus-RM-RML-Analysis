"""Execute original app instructions; Core boundaries use separately run actual CCL.
No Core firmware body is loaded. RTTI is an intentional supported-type adaptation.
"""
import hashlib,itertools,json,pathlib,random,struct,subprocess
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ROOT=pathlib.Path(__file__).resolve().parents[4]
TASK='rolling10_next100_scenes_disconnect'
BASE=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared-next-flow01')
def sha(b):return hashlib.sha256(b).hexdigest()
def seeds():
 sequences=[list(s) for n in range(4) for s in itertools.product(range(5),repeat=n)]
 rng=random.Random(494);sequences += [[rng.randrange(5) for _ in range(n)] for n in [4,7,16,65,129] for _ in range(4)]
 return [dict(mask=m,repeats=r,items=s) for s in sequences for m in range(4) for r in [1,2]]
def payload(s):return ' '.join(map(str,[s['mask'],s['repeats'],len(s['items']),*s['items']]))+'\n'
def generate(exe):
 req=json.loads((BASE/'packets'/TASK/'request.json').read_text());t=req['targets'][0]
 bind=json.loads((ROOT/'temp/recovery-work/rolling10x10-20261114/READ_INPUTS-prepared-next-flow01-rolling10_presets.json').read_text());elf=pathlib.Path(bind['rootfs/CS18_v13840/home/root/surface']['frozen_read_path']);blob=elf.read_bytes();assert sha(blob)==t['original_elf_sha256']
 with elf.open('rb') as f:
  e=ELFFile(f);syms=e.get_section_by_name('.symtab');sym=syms.get_symbol_by_name(t['mangled'])[0];sec=e.get_section(sym['st_shndx']);off=sec['sh_offset']+sym['st_value']-sec['sh_addr'];body=blob[off:off+140];assert sha(body)=='e95d13862695310482538e480c129f7516711d1212cf706f8654a7acf7798885'
  identities=[]
  for name,addr,size in [('_ZTIN4Core8Portable9ParameterE',2118576,12),('_ZTIN4Core8Portable10AliasParamE',2118344,32),('_ZN4Core8Portable10AliasParam11setOriginalEPNS0_9ParameterE',1183268,None)]:
   s=syms.get_symbol_by_name(name)[0];assert s['st_value']==addr and (size is None or s['st_size']==size);identities.append(dict(name=name,address=addr,size=s['st_size'],section=s['st_shndx']))
 inputs=seeds();text=''.join(map(payload,inputs));p=subprocess.run([str(exe),'providers'],input=text,text=True,capture_output=True,check=True);classes=[list(map(int,s.split())) for s in p.stdout.splitlines()];assert len(classes)==len(inputs)
 cases=[];oracle=[]
 for s,cast in zip(inputs,classes):
  assert len(cast)==len(s['items']);u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0xb4000,4096);u.mem_write(t['address'],body);u.mem_map(0xa000,4096);u.mem_map(0x120000,4096);obj=0x1000000;arr=obj+0x1000;pool=obj+0x2000;stop=obj+0xf000;stack=0x9000000;u.mem_map(obj,0x10000);u.mem_map(stack,0x10000)
  def word(a,v):u.mem_write(a,struct.pack('<I',v))
  word(obj+240,arr);word(obj+244,len(cast))
  for i,item in enumerate(s['items']):word(arr+i*4,pool+item*16 if item else 0)
  before=bytes(u.mem_read(obj,0x4000));calls=[];pcs=[];writes=[]
  def hook(uc,pc,n,_):
   if pc==stop:uc.emu_stop();return
   if pc==44632:
    index=uc.reg_read(UC_ARM_REG_R4)-1;ptr=uc.reg_read(UC_ARM_REG_R0);assert ptr==pool+s['items'][index]*16;assert [uc.reg_read(x) for x in [UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]]==[2118576,2118344,0];calls.append(['cast',index,cast[index]]);uc.reg_write(UC_ARM_REG_R0,ptr if cast[index] else 0);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
   if pc==1183268:
    index=uc.reg_read(UC_ARM_REG_R4)-1;assert cast[index] and uc.reg_read(UC_ARM_REG_R0)==pool+s['items'][index]*16 and uc.reg_read(UC_ARM_REG_R1)==0;calls.append(['setOriginal',index]);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
   assert t['address']<=pc<t['address']+128,hex(pc);pcs.append(pc)
  def write(uc,ac,a,n,v,_):assert stack<=a and a+n<=stack+0x10000;writes.append([a-stack,n,v])
  u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
  for _ in range(s['repeats']):
   for reg,v in [(UC_ARM_REG_R0,obj),(UC_ARM_REG_SP,stack+0x8000),(UC_ARM_REG_LR,stop)]:u.reg_write(reg,v)
   u.emu_start(t['address'],stop+4,count=20000);assert u.reg_read(UC_ARM_REG_PC)==stop
  assert bytes(u.mem_read(obj,0x4000))==before
  indices=[c[1] for c in calls if c[0]=='setOriginal'];oracle.append(payload(s).rstrip()+' '+str(len(indices))+' '+ ' '.join(map(str,indices))+'\n');cases.append(dict(input=s,provider_casts=cast,calls=calls,executed_pcs=sorted(set(pcs)),stack_writes=writes,application_state_unchanged=True))
 result=subprocess.run([str(exe),'oracle'],input=''.join(oracle),text=True,capture_output=True,check=True).stdout.splitlines();assert len(result)==len(cases)
 for c,out in zip(cases,result):c['provider_effects']=out
 return dict(task_id=TASK,elf_sha256=t['original_elf_sha256'],range=dict(address=t['address'],size=140,file_offset=off,section='.text',sha256=sha(body)),identities=identities,cases=cases,limitations='Stable borrowed extra vector and live actual Parameter objects; actual supported cast adapts original RTTI, no original Core execution. No reentrant vector mutation, original base/lifecycle/return/layout/ARM ABI or hardware claim.')
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--exe',required=True);p.add_argument('--out',required=True);a=p.parse_args();pathlib.Path(a.out).write_text(json.dumps(generate(pathlib.Path(a.exe).resolve()),indent=2)+'\n')
