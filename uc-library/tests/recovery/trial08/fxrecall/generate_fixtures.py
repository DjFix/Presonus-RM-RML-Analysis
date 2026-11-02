"""Regenerate independent fixture observations by executing the original ELF."""
import copy,json
from pathlib import Path
from oracle import run
BASE=Path(__file__).resolve().parent
methods=[('onIdle',0x553b0),('getSlotNum',0x54818),('cacheUpdated',0x564fc),('isSlotEmpty',0x56030),('isChildParameter',0x553c4),('paramChanged',0x56598),('getFileName',0x55f84),('getFxName',0x56080),('init',0x56640),('updateFxName',0x56148)]
cases=[]
def add(method,address,**overrides):
 c=dict(method=method,address=address,slot=2.75,loaded=1,type=1,effect=0,path='uc-library/tests/recovery/trial08/fxrecall/missing.txt',exists=0,arg=1,children=0,registered=0,cache=True,msg=2)
 c.update(overrides);c['native_observation']={};c['expected']=run(c,c['native_observation'])
 if method=='getSlotNum' and c['expected']['return']>=2**31:c['expected']['return']-=2**32
 cases.append(c)
for method,address in methods:
 for variant in range(2):
  add(method,address,effect=variant*2,path='uc-library/tests/recovery/trial08/fxrecall/existing.txt' if variant else 'uc-library/tests/recovery/trial08/fxrecall/missing.txt',exists=variant,arg=0 if method=='paramChanged' else variant+1,children=variant*3,registered=variant)
for slot in [-7.75,-0.75,0,1.99,19.25]:add('getSlotNum',0x54818,slot=slot)
for msg,arg in [(0,0),(1,0),(2,1),(3,1),(3,4),(3,3),(4,0),(6,0)]:add('paramChanged',0x56598,msg=msg,arg=arg)
for effect,count in [(0,9),(2,4)]:
 for typ in range(count):add('updateFxName',0x56148,loaded=2,type=typ,effect=effect)
add('init',0x56640,cache=False)
(BASE/'fixtures.json').write_text(json.dumps(cases,indent=2)+'\n')
print('Executed original ARM cases:',len(cases))
