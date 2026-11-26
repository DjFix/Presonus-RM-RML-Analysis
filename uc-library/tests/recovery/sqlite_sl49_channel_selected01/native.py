"""Exact native selector+deselect+Mappable bodies; Core parameter/RTTI/provider boundaries explicit."""
import importlib.util,json,struct
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0 as R0,UC_ARM_REG_R1 as R1,UC_ARM_REG_R2 as R2,UC_ARM_REG_R3 as R3,UC_ARM_REG_PC as PC,UC_ARM_REG_LR as LR,UC_ARM_REG_SP as SP
ROOT=Path(__file__).resolve().parents[4]
spec=importlib.util.spec_from_file_location('family_native',ROOT/'uc-library/tests/recovery/sl_channel49/native_common.py');family=importlib.util.module_from_spec(spec);spec.loader.exec_module(family)
PACKET=Path('temp/recovery-work/rolling-c001-20261124/packeting/sqlite-cycle02/sl_channel49_sol61/channel-selected-scope01/packet01/tasks/sqlite_sl49_channel_selected01/CONTEXT.json')
A=0x26000000;STOP=family.STOP;STACK=family.STACK

def cases():
 return [dict(depth=d,slave=s,transition=t,relation='distinct',mutate=False) for d in [0,1,2] for s in [False,True] for t in ['null','same','select','clear','other']]+[dict(depth=2,slave=True,transition='select',relation=r,mutate=m) for r in ['distinct','same','selection_null','linked_null','both_null'] for m in [False,True]]
def run(image,o,c):
 image.verify(o);u=image.cpu();u.mem_map(A,0x100000)
 def put(a,*v):u.mem_write(a,family.pack(*v))
 def word(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 start=A;root=A+c['depth']*0x2000;slave=A+0x6000;mixvt=A+0x10000;groups={};channels=set();values={};indices={};requests=[];callbacks=[];writes=[];entered={}
 group_method=next(n for n in image.symbols if n.startswith('_ZNK8Presonus24MixerClientComponentBase15getChannelGroupE'))
 put(mixvt+0x20,image.symbols[group_method])
 for i in range(c['depth']+1):put(A+i*0x2000,mixvt);put(A+i*0x2000+0x678,A+(i+1)*0x2000 if i<c['depth'] else 0)
 put(slave,mixvt);put(root+0x67c,slave if c['slave'] else 0)
 numeric=image.symbols['_ZTVN4Core8Portable12NumericParamE']+8;channelvt=image.symbols['_ZTVN8Presonus9SLChannelE']+8
 def channel(index):
  ptr=A+0x20000+index*0x400;param=A+0x50000+index*64;put(ptr,channelvt);put(ptr+0x200,param);put(ptr+0x204,0);put(param,numeric);channels.add(ptr);values[param]=family.bits(1.);indices[param]=index;return ptr,param
 roots=[]
 for role,mixer in enumerate([root,slave]):
  for t in range(9):
   index=role*12+t+2;ptr,param=channel(index);group=A+0x80000+(role*9+t)*0x200;items=group+0x100;put(items,ptr);put(group+0x58,items,1);groups[(mixer,t)]=group
   if role==0:roots.append((ptr,param))
 src,sp=channel(0);peer,pp=channel(1);group=groups[(root,0)];put(group+0x100,src,peer,roots[0][0],0,A+0x70000);put(group+0x5c,5)
 signal,sigp=channel(24)
 relation=c['relation'];put(src+0x200,0 if relation in ['selection_null','both_null'] else sp);put(src+0x204,0 if relation in ['linked_null','both_null'] else sp if relation=='same' else pp)
 transition=c['transition'];initial=src if transition in ['same','clear','other'] else 0;incoming=0 if transition in ['null','clear'] else roots[1][0] if transition=='other' else src;put(root+0x680,initial)
 observer1=A+0x71000;observer2=A+0x71100;obvt=A+0x71200;roster=A+0x71300;put(observer1,obvt);put(observer2,obvt);put(obvt,STOP+0x10,STOP+0x14);put(roster,observer1);put(root+0x10,roster,1)
 def ret(v=None):
  if v is not None:u.reg_write(R0,v)
  u.reg_write(PC,u.reg_read(LR))
 def hook(machine,pc,size,user):
  a,b,d=[machine.reg_read(r) for r in (R0,R1,R2)];syms=image.at.get(pc,[])
  if pc==image.symbols[group_method]:requests.append([0 if a==root else 1,b]);ret(groups.get((a,b),0));return
  if pc==image.imports['__dynamic_cast']:
   assert b==image.symbols['_ZTIN4Core8Portable9ComponentE'] and d==image.symbols['_ZTIN8Presonus13SLChannelBaseE'];ret(a if a in channels else 0);return
  if '_ZN4Core8Portable12NumericParam8setValueEfb' in syms:
   assert a in values and d==0;values[a]=b;writes.append([indices[a],b,d]);ret();return
  if pc in [STOP+0x10,STOP+0x14]:
   who=1 if a==observer1 else 2;callbacks.append(('S' if pc==STOP+0x10 else 'O')+str(who)+((':'+str(b)) if pc==STOP+0x14 else ''))
   if pc==STOP+0x10 and c['mutate']:put(roster,observer2)
   ret();return
  for n in syms:
   if n.startswith(('_ZN4Core','_ZNK4Core')):raise RuntimeError('unexpected Core body '+n)
   if n.startswith(('_ZN8Presonus','_ZNK8Presonus')) and n in image.rows:entered[n]=image.rows[n]
 u.hook_add(UC_HOOK_CODE,hook)
 for reg,val in [(R0,start),(R1,incoming),(SP,STACK+0x8000),(LR,STOP)]:u.reg_write(reg,val)
 u.emu_start(o['address'],STOP,count=100000);assert (u.reg_read(PC),u.reg_read(SP))==(STOP,STACK+0x8000)
 final=[values[p] for p in sorted(values,key=lambda p:indices[p])]
 assert values[sigp]==family.bits(1.)
 before=list(callbacks)
 for reg,val in [(R0,start),(R1,incoming),(SP,STACK+0x8000),(LR,STOP)]:u.reg_write(reg,val)
 u.emu_start(o['address'],STOP,count=100000);assert callbacks==before
 return dict(input=c,values=final,parameter_indices=sorted(indices.values()),callbacks=callbacks,group_requests=requests,parameter_writes=writes,cache_matches=word(root+0x680)==incoming,native_app_ranges=entered)
def observe():
 out=[]
 for row in json.loads((ROOT/PACKET).read_text())['originals']:
  o=row['original'];image=family.Image(o)
  out.append(dict(original=o,cases=[run(image,o,c) for c in cases()]))
 return dict(domain='Forty finite cases per role: master depth0/1/2, optional slave, null/same/select/clear/other transitions, five selection/linked aliases, populated groups0..8, null/wrong-type child, signalgen excluded, real native Mappable observer-list reread and identical repeat no-op. Core getter/RTTI/setValue boundaries explicit.',originals=out)
if __name__=='__main__':print(json.dumps(observe(),indent=2))
