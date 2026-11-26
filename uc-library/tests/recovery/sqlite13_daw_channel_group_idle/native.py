"""Observe actual inherited Core onIdle entry in both original role ranges."""
import importlib.util,json,sys
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0 as R0
spec=importlib.util.spec_from_file_location('group_init_machine','uc-library/tests/recovery/sqlite07_daw_channel_group_production_init/native.py')
init=importlib.util.module_from_spec(spec);sys.modules[spec.name]=init;spec.loader.exec_module(init)
GROUP_INIT='_ZN8Presonus15DAWChannelGroup4initEb'
IDLE='_ZN4Core8Portable9Component6onIdleEv'
GET='_ZNK8Presonus15DAWChannelGroup12getUsedCountEv'
def observe(original):
 cases=[]
 for value,count in ((0,4),(-2,4),(1,0),(1,4),(2,4),(4,4),(8,4)):
  m,g,u,children,channels,trace=init.setup(original,0,count,value)
  m.invoke(GROUP_INIT,g,0)
  calls=[];used=[]
  def hook(uc,address,size,data):
   a=uc.reg_read(R0)
   if address==m.address(GET): used.append(a)
   elif a in children: calls.append(children.index(a))
  for name in (IDLE,GET):
   address=m.address(name);m.uc.hook_add(UC_HOOK_CODE,hook,begin=address,end=address)
  for child in children:
   assert m.load(m.load(child)+0x28)==m.address(IDLE)
  m.invoke(original['mangled'],g)
  assert used==[g]
  assert calls==list(range(max(0,min(value,count))))
  cases.append(dict(value=value,count=count,used_calls=len(used),calls=calls,expected=['used '+str(min(value,count)), 'idle '+','.join(map(str,calls))]))
 return dict(original=original,cases=cases)
def run(packet): return [observe(e['original']) for e in json.loads(Path(packet).read_text())['originals']]
if __name__=='__main__': print(json.dumps(run(sys.argv[1]),indent=2))
