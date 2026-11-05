"""Canonical CTest adapter: explicit built executable and hash-bound fixture."""
from pathlib import Path
import json,subprocess,sys
assert len(sys.argv)==3,'expected BUILT_EXECUTABLE FIXTURES'
exe=Path(sys.argv[1]);fixtures=Path(sys.argv[2]);cs=json.loads(fixtures.read_text())['cases'];lines=[]
for c in cs:
 t=c['target'];fields=[t]+([c['count']] if t==1 else c['rectangle'] if t==2 else [c['last'],c['now_ns']]);lines.append(' '.join(map(str,fields)))
p=subprocess.run([str(exe)],input='\n'.join(lines)+'\n',text=True,capture_output=True);assert p.returncode==0,(p.returncode,p.stderr);outputs=p.stdout.splitlines();assert len(outputs)==len(cs)
for c,line in zip(cs,outputs):
 values=list(map(int,line.split()));t=c['target'];expected=c['expected']
 if t==1:assert values==[expected['count']]*3+[8]+[1]*expected['count'],(c,values)
 elif t==2:
  rect=expected['trace'][0]['rectangle'];width=rect[2]-rect[0];height=rect[3]-rect[1];assert values==rect+[width if width>0 and height>0 else 0],(c,values)
 else:assert values==[expected['last'],c['now_ns'],0 if any(x['call']=='rebuildCurves' for x in expected['trace']) else 1],(c,values)
print(json.dumps({'passed':True,'cases':len(cs),'scope':'Actual setter/onIdle entry and dirty-band transition; real pinned CCL with deterministic test-only clock_gettime wrapping.'}))
