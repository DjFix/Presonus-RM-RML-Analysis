from pathlib import Path
import json,subprocess,sys,math
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
EXE=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'temp/recovery-work/rolling200-02/eq-curves/driver'
FIX=Path(sys.argv[2]) if len(sys.argv)>2 else HERE/'curve-fixtures.json'

def input_line(c):
 t=c['target'];v=[t,c.get('type',3),c.get('index',0),c.get('samples',8),c.get('present',1),c.get('q',.7),c.get('frequency',1000.),c.get('gain',6.),c.get('minimum',20.),c.get('maximum',20000.),c.get('buffered',0)]
 if t==4:
  count=c.get('count',1);v.append(count)
  for i,b in enumerate(c.get('bands',[{}]*count)):
   v += [b.get('type',c.get('type',3)),b.get('gain',c.get('gain',6.)),b.get('q',c.get('q',.7)),b.get('frequency',c.get('frequency',1000.)),b.get('on',1),c.get('dirty',[1]*count)[i],b.get('force',0),b.get('initial_on',0),b.get('initial_enabled',0),b.get('initial_frequency',0.),b.get('initial_gain',0.),b.get('initial_curve',123.)]
 return ' '.join(map(str,v))
cs=json.loads(FIX.read_text())['cases'];p=subprocess.run([str(EXE)],input='\n'.join(input_line(c) for c in cs)+'\n',text=True,capture_output=True);assert p.returncode==0,(p.returncode,p.stderr);lines=p.stdout.splitlines();assert len(lines)==len(cs)
maximum=0.;worst=None
for i,(c,line) in enumerate(zip(cs,lines)):
 actual=list(map(float,line.split()));e=c['expected'];exact=set()
 if c['target']==3:
  expected=[e['result']]+(e['curves'][0] if e['curves'] else []);exact.add(0)
 else:
  expected=[e['valid'],e['invalidations']];exact.update([0,1])
  for b in e['bands']:
   start=len(expected);expected += [b[k] for k in ['dirty','on','enabled','frequency','gain','x','y']];exact.update([start,start+1,start+2,start+5,start+6])
  if c.get('samples',8)>0:
   expected+=e['sum']
   if not c.get('buffered',0):
    start=len(expected);expected+=e['pixels'];exact.update(range(start,len(expected)))
 assert len(actual)==len(expected),(i,c,len(actual),len(expected),actual)
 for j,(a,b) in enumerate(zip(actual,expected)):
  if j in exact:assert a==b,(i,j,c,a,b)
  else:
   delta=abs(a-b)
   if delta>maximum:maximum=delta;worst=[i,j,a,b]
   assert math.isfinite(a) and math.isfinite(b) and delta<=0.0002+abs(b)*0.00002,(i,j,c,a,b,delta)
print(json.dumps({'passed':True,'cases':len(cs),'maximum_absolute_error':maximum,'worst':worst,'tolerance':'2e-4 absolute + 2e-5 relative for float responses; integer/flags/pixels exact; bounded corpus only'}))
