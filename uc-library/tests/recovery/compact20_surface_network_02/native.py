"""Execute original application bodies; capture Core boundaries without executing Core.
The deleting destructor's own BL reaches the allocator boundary: that boundary
unmaps the live object page. No delete event is appended after execution.
"""
import hashlib, io, itertools, json, pathlib, struct
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_PROT_ALL
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC
ROOT=pathlib.Path(__file__).resolve().parents[4]
PACKETS='temp/recovery-work/compact-10x20-20261113/generated-implementation40/prepared03/packets'
TASKS=(2,3,4,5,11,12)
OBJ=0x50000000
HEAP=0x40000000
STOP=0x60000000
STACK=0x70000000
EXPECTED_ELF='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
def word(v): return struct.pack('<I',v&0xffffffff)
def generate(elf_path):
 raw=pathlib.Path(elf_path).read_bytes()
 assert hashlib.sha256(raw).hexdigest()==EXPECTED_ELF
 elf=ELFFile(io.BytesIO(raw));symtab=elf.get_section_by_name('.symtab')
 segments=[(s['p_vaddr'],s.data()) for s in elf.iter_segments() if s['p_type']=='PT_LOAD']
 targets={};ranges=[]
 for task in TASKS:
  p=ROOT/PACKETS/f'compact20_surface_network_{task:02}'
  req=json.loads((p/'request.json').read_text());t=req['targets'][0]
  symbols=[s for s in symtab.get_symbol_by_name(t['mangled']) if s['st_value']==t['address'] and s['st_size']==t['size']]
  assert len(symbols)==1
  s=symbols[0];sec=elf.get_section(s['st_shndx']);offset=sec['sh_offset']+s['st_value']-sec['sh_addr']
  body=json.loads((p/'native-context.json').read_text());body=body['bodies'][body['roots'][0]]
  digest=hashlib.sha256(raw[offset:offset+t['size']]).hexdigest()
  assert offset==body['file_offset'] and digest==body['bytes_sha256']
  targets[task]=t
  ranges.append(dict(task=task,original_elf_sha256=EXPECTED_ELF,mangled=t['mangled'],address=t['address'],size=t['size'],section=s['st_shndx'],file_offset=offset,range_sha256=digest))
 def execute(task,args):
  uc=Uc(UC_ARCH_ARM,UC_MODE_ARM);uc.mem_map(0x8000,0x3f8000)
  for address,data in segments:uc.mem_write(address,data)
  for address,size in [(OBJ,0x1000),(HEAP,0x10000),(STOP,0x1000),(STACK,0x10000)]:uc.mem_map(address,size)
  uc.reg_write(UC_ARM_REG_SP,STACK+0xf000);uc.reg_write(UC_ARM_REG_LR,STOP);uc.reg_write(UC_ARM_REG_R0,OBJ)
  trace=[];aliases={};paramkinds={};localtags={};channelparams={};live={OBJ};return_values={}
  def put(address,value):uc.mem_write(address,word(value))
  if task==3:
   index,flag,k0,k1,mask=map(int,args[1:]);uc.reg_write(UC_ARM_REG_R1,HEAP+0x4000);uc.reg_write(UC_ARM_REG_R2,index&0xffffffff);uc.reg_write(UC_ARM_REG_R3,flag)
   for i,kind in enumerate([k0,k1]):
    ptr=HEAP+0x1000+i*0x100;tag=(index+[0x76,0x78][i])&0xffffffff
    if kind:localtags[tag]=ptr;paramkinds[ptr]=kind
    if kind==1:aliases[ptr]=0
    if mask&(1<<i):channelparams[[302,300][i]]=HEAP+0x2000+i*0x100
  if task==4:
   pattern=args[1];put(OBJ+0xdc,len(pattern));put(OBJ+0xd8,HEAP)
   for i,kind in enumerate(pattern):
    ptr=HEAP+0x1000+i*0x100 if kind!='0' else 0;put(HEAP+i*4,ptr)
    if ptr:paramkinds[ptr]=int(kind)
    if kind=='1':aliases[ptr]=HEAP+0x3000
  if task in (11,12):
   tag,mask=map(int,args[1:]);channelparams={400+i:HEAP+0x2000+i*0x100 for i in range(2) if mask&(1<<i)}
  def capture(uc,address,size,user):
   if address==STOP:uc.emu_stop();return
   if targets[task]['address']<=address<targets[task]['address']+targets[task]['size']:return
   r0=uc.reg_read(UC_ARM_REG_R0);r1=uc.reg_read(UC_ARM_REG_R1);r2=uc.reg_read(UC_ARM_REG_R2)
   result=0
   if address==0x11f24c:
    assert task==3 and r0==OBJ+0x28
    result=localtags.get(r1,0);trace.append(['ParamList.byTag',r1,result])
   elif address==0xae58:
    result=r0 if paramkinds.get(r0)==1 else 0;trace.append(['dynamic_cast.AliasParam',r0,result])
   elif address==0x11acf0:
    assert r0==(HEAP+0x4000 if task==3 else OBJ)
    result=channelparams.get(r1,0);trace.append(['Component.getParameterByTag',r1,result]);return_values[result]=r1 if result else 0
   elif address==0x120e24:
    assert r0 in aliases;aliases[r0]=r1;trace.append(['AliasParam.setOriginal',r0,r1])
   elif address in (0x25ec0,0x613bc,0x5d36c,0x11b5e0):
    assert task in (2,5)
    name={0x25ec0:'bits_storage',0x613bc:'mappables_storage',0x5d36c:'inherited_alias_storage',0x11b5e0:'component_base'}[address]
    expected={0x25ec0:OBJ+0xf0,0x613bc:OBJ+0xd4,0x5d36c:OBJ+0xb4,0x11b5e0:OBJ}[address]
    assert r0==expected;trace.append([name,r0])
   elif address==0xad5c:
    assert task==5 and r0 in live
    uc.mem_unmap(r0,0x1000);live.remove(r0);trace.append(['allocator_unmapped',r0])
   else:raise AssertionError(('unexpected execution outside original app body',hex(address)))
   uc.reg_write(UC_ARM_REG_R0,result);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  uc.hook_add(UC_HOOK_CODE,capture);uc.emu_start(targets[task]['address'],STOP,count=10000)
  assert uc.reg_read(UC_ARM_REG_PC)==STOP
  if task==3:
   output=[]
   for i in range(2):
    ptr=localtags.get((int(args[1])+[0x76,0x78][i])&0xffffffff,0);value=aliases.get(ptr,0)
    output.append(next((tag for tag,p in channelparams.items() if p==value),0))
   expected=f'{output[0]} {output[1]}\n'
  elif task==4:
   assert all(x==0 for x in aliases.values());expected='0\n'
  elif task in (11,12):expected=str(return_values.get(uc.reg_read(UC_ARM_REG_R0),0))+'\n'
  else:
   assert [x[0] for x in trace[:4]]==['bits_storage','mappables_storage','inherited_alias_storage','component_base']
   assert (OBJ not in live)==(task==5);expected=str(int(OBJ not in live))+'\n'
  return dict(task=task,argv=args,expected=expected,native_boundary_trace=trace,actual_native_instructions_executed=True)
 cases=[]
 for task in (11,12):
  for mask in range(4):cases.append(execute(task,['get',str(400 if task==11 else 401),str(mask)]))
 for index,flag,k0,k1,mask in itertools.product([0,-118,-2147483648,2147483647],[0,1],range(3),range(3),[0,3]):
  cases.append(execute(3,['connect',str(index),str(flag),str(k0),str(k1),str(mask)]))
 for mask in (1,2):cases.append(execute(3,['connect','0','0','1','1',str(mask)]))
 for pattern in ('','0','1','2','012','111','20101','1022101'):cases.append(execute(4,['disconnect',pattern]))
 for task in (2,5):cases.append(execute(task,['life',str(int(task==5))]))
 return dict(version=1,elf_sha256=EXPECTED_ELF,ranges=ranges,cases=cases,oracle_scope='Original application instructions; Core/runtime boundaries intercepted, never original Core execution. D0 BL invokes modeled allocator which actually unmaps live emulator memory; real C++ allocator/lifecycle checked separately.',exclusions=['exception unwinding','original return declaration','original private layout','ARM ABI interoperability','concurrently mutated mappables'],producer_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest())
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--elf',required=True);p.add_argument('--out',required=True);a=p.parse_args();pathlib.Path(a.out).write_text(json.dumps(generate(a.elf),indent=2)+'\n')
