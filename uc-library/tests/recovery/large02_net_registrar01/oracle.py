"""Exact assigned ARM execution. Core/runtime calls are modeled boundaries only."""
import argparse, hashlib, json, struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC
BASE=Path('temp/recovery-work/large02-network-owning03/batch02/packets')
OBJ=0x2000000; STOP=0x3000000

def load():
 result=[]
 for i in range(1,9):
  p=BASE/f'large02_net_registrar01_{i:02}'
  req=json.loads((p/'request.json').read_text()); ctx=json.loads((p/'context.json').read_text())
  for original in req['originals']:
   o=original['original']; role=o['role']; path=Path('rootfs/CS18_v13840/home/root/surface' if role=='client' else 'rootfs/RML16AI_Rack_13731/home/root/mixer')
   raw=path.read_bytes(); assert hashlib.sha256(raw).hexdigest()==o['elf']
   body=next(b for b in ctx['native_context']['bodies'].values() if b['address']==o['address'])
   assert hashlib.sha256(raw[body['file_offset']:body['file_offset']+body['size']]).hexdigest()==body['bytes_sha256']
   result.append(dict(index=i,original=o,body=body,path=str(path)))
 return result

def execute(target, rows, n, holes, storage):
 role=target['original']['role']; i=target['index']; rows=[r for r in rows if r['original']['role']==role]
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x1000000);u.mem_map(OBJ,0x100000);u.mem_map(STOP,0x10000)
 with open(target['path'],'rb') as f:
  elf=ELFFile(f)
  for seg in elf.iter_segments():
   if seg['p_type']=='PT_LOAD':u.mem_write(seg['p_vaddr'],seg.data())
  names={}
  for sym in elf.get_section_by_name('.symtab').iter_symbols():
   if sym['st_info']['type']=='STT_FUNC': names.setdefault(sym['st_value'],[]).append(sym.name)
 def wr(a,v):u.mem_write(a,struct.pack('<I',v))
 def rd(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 trace=[]; writes=[]; dealloc=[]; buffers={};objects={}
 def buffer(vec,label,count):
  ptr=OBJ+0x40000+len(buffers)*0x1000 if count else 0
  wr(vec+4,ptr);wr(vec+8,count);wr(vec+12,5 if count else 0);wr(vec+16,5)
  if ptr:buffers[ptr]=label
  return ptr
 remote=next(r for r in rows if r['index']==6)
 if i in [3,4]:
  buffer(OBJ,'local',2); arr=buffer(OBJ+0x14,'remote',n);buffer(OBJ+0x28,'listener',2)
  for k in range(n):
   if holes and k%2==1:wr(arr+k*4,0);continue
   q=OBJ+(k+1)*0x1000;vt=OBJ+0x20000+k*0x100
   objects[q]=f'remote{k}';wr(q,vt);wr(vt+4,remote['body']['address']);wr(arr+k*4,q)
   buffer(q+0x110,f'storage{k}',storage)
 elif i>=5:
  objects[OBJ]='object';buffer(OBJ+0x110,'storage',storage)
 else:u.mem_write(OBJ,bytes([0xa5])*0x100)
 def ret():u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 allowed=set()
 for row in rows:
  allowed.update(x['address'] for x in row['body']['instructions'])
 def memory(uc,access,address,size,value,data):
  if OBJ <= address < OBJ+0x10000:writes.append(dict(address=address,size=size,value=value))
 def hook(uc,pc,size,data):
  if pc==STOP:uc.emu_stop();return
  if pc in allowed:return
  a=uc.reg_read(UC_ARM_REG_R0);ns=names.get(pc,[])
  if any('6resizeEi' in x and 'Vector' in x for x in ns):
   assert uc.reg_read(UC_ARM_REG_R1)==0 and rd(a+4)==0 and rd(a+8)==0
   ret();return
  if any('Vector' in x and 'D1Ev' in x for x in ns):
   ptr=rd(a+4)
   if ptr:
    label=buffers.pop(ptr);trace.append(['free',label]);dealloc.append(dict(address=ptr,size=4096,boundary='modeled Core container cleanup'));uc.mem_unmap(ptr,4096)
   ret();return
  if any(x.startswith('_ZdlPv') for x in ns):
   trace.append(['delete',objects.pop(a)]);dealloc.append(dict(address=a,size=4096,boundary='observed app operator delete call; modeled heap unmap'));uc.mem_unmap(a,4096);ret();return
  raise RuntimeError((hex(pc),ns,hex(a)))
 u.hook_add(UC_HOOK_MEM_WRITE,memory);u.hook_add(UC_HOOK_CODE,hook)
 u.reg_write(UC_ARM_REG_R0,OBJ);u.reg_write(UC_ARM_REG_SP,STOP+0xf000);u.reg_write(UC_ARM_REG_LR,STOP)
 u.emu_start(target['body']['address'],STOP,count=100000)
 assert u.reg_read(UC_ARM_REG_PC)==STOP
 observed={'trace':trace}
 if i<=2:observed['initial']=[rd(OBJ+8),rd(OBJ+0x1c),rd(OBJ+0x30),rd(OBJ+0x10),rd(OBJ+0x24),rd(OBJ+0x38)]
 return dict(observed=observed,raw_writes=writes,native_modeled_deallocation=dealloc)

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();rows=load();cases=[]
 for r in rows:
  domain=[(0,False,0)] if r['index']<=2 else ([(n,h,s) for n in [0,1,3,5] for h in [False,True] for s in [0,3]] if r['index']<=4 else [(0,False,s) for s in [0,1,3,7]])
  for n,h,s in domain:cases.append(dict(index=r['index'],role=r['original']['role'],count=n,holes=h,storage=s,native=execute(r,rows,n,h,s)))
 ranges=[dict(index=r['index'],original=r['original'],**{k:r['body'][k] for k in ['address','size','section','file_offset','bytes_sha256']}) for r in rows]
 Path(a.out).write_text(json.dumps(dict(oracle='Unicorn exact app instructions; explicit modeled Core resize/destructor and runtime delete boundaries, no target Core/libc execution',ranges=ranges,cases=cases),indent=2)+'\n')
 print('native cases',len(cases))
if __name__=='__main__':main()
