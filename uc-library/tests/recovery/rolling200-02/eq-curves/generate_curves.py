from pathlib import Path
import json,sys,time
from curve_native import execute,SHA
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[5] if False else HERE.parents[5-1]
OUT=HERE/'curve-fixtures.json';AUDIT=HERE/'native-execution.json'
cs=[]
for extras in [{'index':-1},{'index':1},{'present':0},{'q':0},{'minimum':0},{'maximum':0},{'samples':0},{'samples':-1}]:cs.append({'target':3,'type':3,'samples':8,**extras})
for kind in [0,1,2,3,7]:
 for samples in [1,8,64]:
  cs.append({'target':3,'type':kind,'samples':samples,'frequency':1000.,'gain':6.,'q':.7})
for kind,gain,frequency,q in [(0,-6.,200.,1.2),(1,-6.,200.,1.2),(2,-6.,10000.,1.2),(3,-6.,2000.,1.2),(3,0.,1000.,.7),(3,0.025,1000.,.7)]:cs.append({'target':3,'type':kind,'samples':8,'frequency':frequency,'gain':gain,'q':q})
for width,count,buffered,dirty in [(0,1,0,[1]),(1,0,0,[]),(8,0,1,[]),(1,1,0,[1]),(8,1,0,[0]),(8,1,0,[1]),(8,1,1,[1]),(8,3,0,[1,1,1]),(8,3,1,[1,0,1]),(8,3,0,[0,1,0])]:
 bands=[dict(type=i%4,gain=[6.,-3.,.025][i%3],frequency=[200.,2000.,10000.][i%3],q=.7,on=1,force=0,initial_on=1,initial_enabled=1,initial_frequency=500.,initial_gain=1.,initial_curve=2.) for i in range(count)]
 cs.append(dict(target=4,samples=width,count=count,buffered=buffered,dirty=dirty,bands=bands))
for on,gain,force,present in [(0,6.,0,1),(1,0.,0,1),(1,.05,0,1),(1,.025,1,1),(1,-.05,0,1),(1,-.051,0,1),(1,6.,0,0)]:
 cs.append(dict(target=4,samples=8,count=1,buffered=0,present=present,bands=[dict(type=3,gain=gain,frequency=1000.,q=.7,on=on,force=force)]))
fixtures=[];audits=[];started=time.time()
for i,c in enumerate(cs):
 result=execute(c)
 expected={k:result[k] for k in ['result','curves','sum','pixels','bands','valid','invalidations']}
 fixtures.append({**c,'expected':expected})
 audits.append({k:result[k] for k in ['pcs','providers','ranges','bindings','provider_trace','application_calls','writes','runtime_ranges','runtime_proof']})
 OUT.write_text(json.dumps({'elf_sha256':SHA,'cases':fixtures},indent=2)+'\n')
 AUDIT.write_text(json.dumps({'elf_sha256':SHA,'cases':audits,'started':started,'elapsed_seconds':time.time()-started,'no_Core_body_execution':True,'no_host_math':True,'no_syscalls':True,'limitations':'Actual ARM application, libgcc and exact CS18 libm instructions; Core Parameter/interpolator/View boundaries captured; actual pinned CCL provider replay is separate. Injected software FENV capability word; no hardware/ARM ABI/declaration claim.'},indent=2)+'\n')
 print(f'{i+1}/{len(cs)} target{c["target"]} samples{c["samples"]}',flush=True)
