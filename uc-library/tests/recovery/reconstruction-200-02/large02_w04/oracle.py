"""Exact original ARM bodies; external calls are observation boundaries, never Core execution."""
import argparse, hashlib, json, struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
REG=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
PACKETS=Path('temp/recovery-work/reconstruction-200-02/isolated-batch01/packets')
ELF=Path('rootfs/RML16AI_Rack_13731/home/root/mixer')
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
OBJ=0x1000000; PEER=OBJ+0x2000; PARAM=OBJ+0x3000; SAVED=OBJ+0x4000; COMP=OBJ+0x5000; VT=OBJ+0x6000; STOP=0x2000000; STUB=STOP+0x100

def load():
 raw=ELF.read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
 bodies=[]
 for i in range(1,17):
  j=json.loads((PACKETS/f'large02_w04_{i:02}'/'context.json').read_text())
  for b in j['native_context']['bodies'].values():
   data=raw[b['file_offset']:b['file_offset']+b['size']]
   assert hashlib.sha256(data).hexdigest()==b['bytes_sha256']
   bodies.append((i,b))
 return raw,bodies

def run(index,state,raw,bodies):
 uc=Uc(UC_ARCH_ARM,UC_MODE_ARM);uc.mem_map(0,0x800000);uc.mem_map(OBJ,0x10000);uc.mem_map(STOP,0x1000);uc.mem_map(0x3000000,0x10000)
 with ELF.open('rb') as f:
  for seg in ELFFile(f).iter_segments():
   if seg['p_type']=='PT_LOAD':uc.mem_write(seg['p_vaddr'],seg.data())
 def wr(a,v):uc.mem_write(a,struct.pack('<I',v&0xffffffff))
 def rd(a):return struct.unpack('<I',uc.mem_read(a,4))[0]
 def cstr(a):return bytes(uc.mem_read(a,256)).split(b'\0')[0].decode()
 def ret(v=None):
  if v is not None:uc.reg_write(REG[0],v&0xffffffff)
  uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
 wr(OBJ+0x98,PEER if state.get('peer') else 0);wr(OBJ+0xa0,PEER if state.get('selected') else 0)
 wr(OBJ+0x4b8,COMP if state.get('component') else 0);wr(OBJ+0x4bc,PARAM if state.get('parameter') else 0);wr(OBJ+0x4c0,SAVED if state.get('saved') else 0)
 wr(PEER,VT);wr(PARAM,VT+0x100);wr(SAVED,VT+0x200);wr(COMP,VT+0x300)
 for v,o in [(VT,0x28),(VT+0x100,0x44),(VT+0x100,0x58),(VT+0x200,0x44),(VT+0x300,0x14)]:wr(v+o,STUB+o+(v-VT)*2)
 for off,n in [(0x84,state.get('connectors',0)),(0xac,state.get('activators',0))]:
  a=OBJ+0x7000+off*4;wr(OBJ+off,a);wr(OBJ+off+4,n)
  for k in range(n):
   q=OBJ+0x9000+off*8+k*16;wr(a+k*4,q);wr(q,VT+0x500);wr(VT+0x500,STUB+0xe00)
 uc.mem_write(OBJ+0xf000,b'component/path\0')
 uc.reg_write(REG[0],OBJ);uc.reg_write(REG[1],state.get('arg',0)&0xffffffff);uc.reg_write(REG[2],state.get('message',0)&0xffffffff)
 if index==4:uc.reg_write(REG[1],PARAM if state.get('same',True) else SAVED)
 if index==6:uc.reg_write(REG[1],COMP if state.get('component') else 0)
 if index in [14,16]:uc.reg_write(REG[1],OBJ+0xf000);uc.reg_write(REG[2],state.get('arg',0)&0xffffffff)
 uc.reg_write(UC_ARM_REG_SP,0x300f000);uc.reg_write(UC_ARM_REG_LR,STOP)
 trace=[];writes=[];deallocated=[]
 fields={0x4bc:PARAM if state.get("parameter")else 0,0x4b8:COMP if state.get("component")else 0}
 def memory_hook(u,access,address,size,value,_):
  if OBJ <= address < OBJ+0x1000:
   writes.append({'object_offset':address-OBJ,'size':size,'value':value})
   if address-OBJ in fields:fields[address-OBJ]=value
 uc.hook_add(UC_HOOK_MEM_WRITE,memory_hook)
 allowed={b['address']+x*4 for i,b in bodies if i in [index,1,2,5,8,13] for x in range((b['size']+3)//4)}
 # Bodies of assigned originals execute recursively. Boundaries are explicit.
 def hook(u,pc,size,_):
  if pc==STOP:u.emu_stop();return
  if pc in allowed:return
  a=[u.reg_read(x) for x in REG]
  if pc==0x157940:
   v=struct.unpack('<f',struct.pack('<I',a[0]))[0];ret(int(v>0));return
  if pc==STUB+0x244:trace.append(['value','parameter']);ret(struct.unpack('<I',struct.pack('<f',state.get('value',0.0)))[0]);return
  if pc==STUB+0x444:trace.append(['value','saved']);ret(struct.unpack('<I',struct.pack('<f',state.get('saved_value',0.0)))[0]);return
  if pc==STUB+0x258:trace.append(['set',a[1],a[2]]);ret();return
  if pc==STUB+0x28:trace.append(['idle']);ret();return
  if pc==STUB+0x614:trace.append(['child',cstr(a[1])]);ret(OBJ+0xb000 if state.get('global') else 0);return
  if pc==STUB+0xe00:trace.append(['connector',int(a[1]!=0)]);ret();return
  if pc==0xc558:trace.append(['getComponent']);ret(COMP if state.get('component') else 0);return
  if pc==0x119c4c:trace.append(['parameterByTag',a[1]]);ret(PARAM if state.get('found') else 0);return
  if pc==0xff620:trace.append(['sendEvent']);ret();return
  if pc==0x116a38:trace.append(['debug']);ret();return
  if pc==0x11c2e4:trace.append(['removeObserver',int(a[0]==PARAM),int(a[1]==OBJ+4)]);ret();return
  if pc==0x11a53c:trace.append(['baseDestructor']);ret();return
  if pc==0xac10:
   assert a[0]==OBJ
   uc.mem_unmap(OBJ,0x1000);deallocated.append({'address':OBJ,'size':0x1000,'boundary':'observed original operator delete call; modeled heap unmaps object page'})
   trace.append(['delete',1]);ret();return
  if pc==0x1004e4:trace.append(['attributes',cstr(a[1])]);ret();return
  if pc==0x100484:trace.append(['url',cstr(a[1])]);ret();return
  if pc==0x122b78:trace.append(['attribute',cstr(a[1])]);ret(OBJ+0xe000);return
  if pc==0x123a58:trace.append(['integer',a[2],a[3]]);ret();return
  if pc==0x12445c:trace.append(['string',cstr(a[1]),a[2]]);ret();return
  if pc==0x1008e0:trace.append(['event',a[2],a[3]]);ret();return
  if pc==0x10f578:trace.append(['bufferDestructor']);ret();return
  if pc==0x122720:trace.append(['attributesDestructor']);ret();return
  raise RuntimeError(f'Unbound execution {pc:x}, args {a}')
 uc.hook_add(UC_HOOK_CODE,hook)
 b=next(b for i,b in bodies if i==index);uc.emu_start(b['address'],STOP,count=10000)
 assert uc.reg_read(UC_ARM_REG_PC)==STOP,'native did not return'
 return {'native_object_writes':writes,'native_deallocation':deallocated,'trace':trace,'parameter_present':bool(fields[0x4bc]),'component_present':bool(fields[0x4b8]),'result_present':bool(uc.reg_read(REG[0]))}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);args=ap.parse_args();raw,bodies=load();cases=[]
 for i in range(1,17):
  states=[{}, {'peer':True,'selected':True,'component':True,'parameter':True,'saved':True,'global':True,'found':True,'connectors':3,'activators':2,'value':1.0,'saved_value':0.5,'arg':-1,'message':3}]
  if i in [2,3,4,6,8]:
   for val in [-1.0,-0.0,0.0,0.25,float("nan")]:
    for component in [False,True]:states.append(dict(states[1],value=val,component=component,message=5))
  if i in [2,3,6,8]:states.append(dict(states[1],parameter=False))
  if i==3:states.append(dict(states[1],saved=False))
  if i==4:
   for msg in [0,3,5]:states.append(dict(states[1],same=False,message=msg))
  if i in [1,5,11,12,13,14,15,16]:
   for key in ['peer','selected','component','global','found']:states.append(dict(states[1],**{key:False}))
  if i in [14,15,16]:
   for x in [0,1,-2147483648,2147483647]:states.append(dict(states[1],arg=x))
  for s in states:cases.append({'index':i,'state':s,'native':run(i,s,raw,bodies)})
 Path(args.out).write_text(json.dumps({'elf_sha256':SHA,'oracle':'Unicorn exact app instructions with explicit external-call stubs','ranges':[dict(index=i,**{k:b[k] for k in ['address','size','file_offset','section','bytes_sha256']}) for i,b in bodies],'cases':cases},indent=2)+'\n')
 print('native cases',len(cases))
if __name__=='__main__':main()
