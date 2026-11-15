"""Execute only sealed non-Core ranges; CCL/libc and existing cache APIs are
explicit typed boundaries. No provider binary is executed or reconstructed."""
import hashlib,json,pathlib,struct
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ROOT=pathlib.Path(__file__).resolve().parents[4]
BINDING=ROOT/'temp/recovery-work/rolling10x10-20261114/READ_INPUTS-rolling10_presets.json'
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
TASKS=['rolling10_presets_01','rolling10_presets_02','rolling10_presets_03','rolling10_replacement_presets_01']
PACKETS=ROOT/'temp/recovery-work/rolling10x10-20261114/prepared05/packets'
def digest(b):return hashlib.sha256(b).hexdigest()
def generate(task):
 req=json.loads((PACKETS/task/'request.json').read_text());t=req['targets'][0]
 elf=pathlib.Path(json.loads(BINDING.read_text())['rootfs/RML16AI_Rack_13731/home/root/mixer']['frozen_read_path'])
 blob=elf.read_bytes();assert digest(blob)==SHA
 with elf.open('rb') as f:
  e=ELFFile(f);s=e.get_section_by_name('.symtab').get_symbol_by_name(t['mangled'])[0];sec=e.get_section(s['st_shndx']);a=s['st_value'];n=s['st_size'];off=sec['sh_offset']+a-sec['sh_addr'];code=blob[off:off+n]
  assert (a,n,s['st_shndx'])==(t['address'],t['size'],t['section'])
  # Data are read using actual ELF section mappings, never symbol row numbers.
  def at(addr,size):
   for q in e.iter_sections():
    if q['sh_type']!='SHT_NOBITS' and q['sh_addr']<=addr and addr+size<=q['sh_addr']+q['sh_size']:
     return blob[q['sh_offset']+addr-q['sh_addr']:q['sh_offset']+addr-q['sh_addr']+size]
   raise AssertionError(hex(addr))
  seeds=[]
  if task==TASKS[3]:
   for types in [[],['channel'],['channel','reverb'],['channel','channel'],['','channel'],['x'*63]]:
    for url in [None,'','presets/channel/01','presets/channelExtra','xpresets/channel','presets/reverb','PRESETS/channel','presets/'+('x'*63)+'z','a'*300]:seeds.append(dict(types=types,url=url))
  else:
   for types in [[],['channel'],['reverb','channel'],['channel','channel']]:
    for kind in ['channel','reverb','missing']:
     for slot in [-1,0,2,2147483647,-2147483648]:
      for flag in [False,True]:seeds.append(dict(types=types,kind=kind,slot=slot,flag=flag,name=None if flag else 'Voice',category='Vocal' if flag else None))
  cases=[]
  for seed in seeds:
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(a&~4095,8192);u.mem_write(a,code)
   # Map boundary entry pages but never load or run original provider bodies.
   boundaries=[0x84b08,0x857d4,0x85bac,0x85ae0,0x129ba4,0xae98,0xae08,0xad18]
   mapped={a&~4095,(a&~4095)+4096}
   for p in boundaries:
    if p&~4095 not in mapped:u.mem_map(p&~4095,4096);mapped.add(p&~4095)
   obj=0x1000000;stack=0x9000000;stop=obj+0xf000;out=obj+0x9000
   u.mem_map(obj,0x10000);u.mem_map(stack,0x10000)
   def word(p,v):u.mem_write(p,struct.pack('<I',v&0xffffffff))
   def read(p):return struct.unpack('<I',u.mem_read(p,4))[0]
   def put(p,s):u.mem_write(p,s.encode()+b'\0')
   def text(p):
    if p==0:return None
    b=bytearray()
    for i in range(4096):
     x=bytes(u.mem_read(p+i,1))
     if x==b'\0':return b.decode()
     b.extend(x)
    raise AssertionError('unterminated')
   pool=obj+0xa000
   def alloc(s):
    nonlocal pool
    if s is None:return 0
    p=pool;pool+=len(s.encode())+1;put(p,s);return p
   types=seed['types'];cacheptr=[obj+0x1000+i*0x100 for i in range(len(types))]
   word(obj+8,obj+0x8000);word(obj+12,len(types))
   for i,(kind,p) in enumerate(zip(types,cacheptr)):word(obj+0x8000+i*4,p);put(p+4,kind)
   trace=[];pcs=[];writes=[];boundary_pcs=[]
   def norm(p):
    if p in cacheptr:return 'cache'+str(cacheptr.index(p))
    return str(p)
   def hook(uc,pc,size,_):
    if pc==stop:uc.emu_stop();return
    r=[uc.reg_read(x) for x in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]]
    if a<=pc<a+n:pcs.append(pc);return
    boundary_pcs.append(pc);ret=None
    if pc==0x84b08:
     kind=text(r[1]);ret=next((p for k,p in zip(types,cacheptr) if k==(kind or '')),0)
     trace.append(['lookup',kind])
    elif pc==0x857d4:trace.append(['cache',norm(r[0]),text(r[1]),text(r[2]),r[3] if r[3]<2**31 else r[3]-2**32]);ret=0
    elif pc==0x85bac:
     trace.append(['info',norm(r[0]),r[3] if r[3]<2**31 else r[3]-2**32]);put(r[1],'NativeName');put(r[2],'NativeCategory');ret=1 if seed['flag'] else 0
    elif pc==0x85ae0:
     trace.append(['path',norm(r[1]),r[2],r[3]]);put(r[0],'BoundaryPath');ret=r[0]
    elif pc==0x129ba4:
     value=text(r[1]);put(r[0],(value or '')[:255]);ret=r[0]
    elif pc==0xae98:ret=len(text(r[0]))
    elif pc==0xae08:
     put(r[0],text(r[0])+text(r[1])[:r[2]]);ret=r[0]
    elif pc==0xad18:
     hay=text(r[0]);needle=text(r[1]);pos=hay.find(needle);ret=r[0]+pos if pos>=0 else 0
    else:raise AssertionError(('unexpected external',hex(pc)))
    if ret is not None:uc.reg_write(UC_ARM_REG_R0,ret)
    uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
   def memory(uc,access,p,size,value,_):
    if not stack<=p<stack+0x10000:writes.append([p-obj,size,value])
   u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,memory)
   sp=stack+0x8000
   regs=[obj,0,0,0]
   if task==TASKS[0]:regs=[obj,alloc(seed['kind']),alloc(seed['name']),alloc(seed['category'])];word(sp,seed['slot'])
   elif task==TASKS[1]:
    regs=[obj,out,out+128,seed['slot']&0xffffffff];put(out,'OriginalName');put(out+128,'OriginalCategory');word(sp,alloc(seed['kind']))
   elif task==TASKS[2]:regs=[out,obj,seed['slot']&0xffffffff,alloc(seed['kind'])];word(sp,int(seed['flag']));u.mem_map(0x35b000,4096);u.mem_write(0x35b15c,at(0x35b15c,4))
   else:
    regs=[obj,alloc(seed['url']),0,0];u.mem_map(0x158000,4096);u.mem_write(0x158fc0,at(0x158fc0,8))
   for reg,value in zip([UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3],regs):u.reg_write(reg,value)
   u.reg_write(UC_ARM_REG_SP,sp);u.reg_write(UC_ARM_REG_LR,stop)
   u.emu_start(a,stop+4,count=10000);assert u.reg_read(UC_ARM_REG_PC)==stop
   result={}
   if task==TASKS[1]:result=dict(result=u.reg_read(UC_ARM_REG_R0),name=text(out),category=text(out+128))
   elif task==TASKS[2]:result=dict(path=text(out))
   elif task==TASKS[3]:result=dict(index=cacheptr.index(u.reg_read(UC_ARM_REG_R0)) if u.reg_read(UC_ARM_REG_R0) else -1)
   cases.append(dict(input=seed,trace=trace,output=result,executed_pcs=pcs,boundary_pcs=boundary_pcs,memory_writes=writes))
 return dict(task_id=task,elf_sha256=SHA,elf_path=str(elf),range=dict(mangled=t['mangled'],address=a,size=n,section=sec.name,section_index=s['st_shndx'],file_offset=off,sha256=digest(code)),cases=cases,limitations='Only exact target application instructions executed. Existing lookupCache/cache APIs are typed observed routing boundaries, not original callee execution. CCL FileName constructor uses bounded copy boundary checked independently against actual pinned source; libc string boundaries use specified C semantics. No hardware, original layouts, return declaration or ARM ABI claim.')
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--task',required=True);p.add_argument('--out',required=True);a=p.parse_args();pathlib.Path(a.out).write_text(json.dumps(generate(a.task),indent=2)+'\n')
