import json,subprocess,sys
from pathlib import Path
f=json.loads(Path(sys.argv[2]).read_text())
n=0
for original in f['originals']:
 for run in original['runs']:
  b=bytes.fromhex(run['object_bytes_hex']); word=lambda off:int.from_bytes(b[off:off+4],'little')
  expected=[word(4),word(8),word(16),word(20),word(24),b[28],b[29],word(32),word(36),1,1,0]
  result=subprocess.check_output([sys.argv[1],str(run['int_bits']),str(int(run['pointer_bits']!=0))],text=True)
  assert list(map(int,result.split()))==expected,(original['identity']['original_mangled'],run,result)
  n+=1
print(json.dumps({'portable_cases':n,'native_cases':sum(len(o['runs']) for o in f['originals']),'scope':'constructor named-state mapping; native opaque pointers mapped to valid borrowed list/null; descriptor growth and index/tag conversion adapter checks'}))
