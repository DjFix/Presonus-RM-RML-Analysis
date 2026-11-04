import json,subprocess,sys
from pathlib import Path
fixtures=json.loads(Path(sys.argv[2]).read_text());cases=fixtures['cases']
inputs=''.join(' '.join(map(str,[c['task'],*c['args']]))+'\n' for c in cases)
r=subprocess.run([sys.argv[1]],input=inputs,text=True,capture_output=True,check=True)
rows=r.stdout.splitlines();assert len(rows)==len(cases),(len(rows),len(cases),r.stderr)
for i,(case,line) in enumerate(zip(cases,rows)):
    actual=list(map(int,line.split()))
    assert actual==case['output'],(i,case,actual)
print(json.dumps({'passed':len(cases),'domain':'Original setter writes, mapping full int32 edges, encoder clamp/wrap MIDI, normalized finite float fader cache/send, abstract D1 non-deallocation/no payload cleanup, borrowed embedded model identity','normalization':'Native pointer offset +136 maps to actual C++ member identity; native dispatch reset recorded independently; portable D1 compares only no deallocation and preserved payload. Neither asserts ARM layout.'}))
