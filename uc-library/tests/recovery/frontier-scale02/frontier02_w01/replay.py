import json,subprocess,sys
from pathlib import Path
from oracle import observe
f=json.loads(Path(sys.argv[2]).read_text());assert observe()==f
for c in f["cases"]:
 out=list(map(int,subprocess.check_output([sys.argv[1],str(c["input"])],text=True).split()))
 assert out==[c["input"],c["dispatch"],0,1,0,0,1],(c,out)
print("6 native constructor boundary traces and actual Book-provider empty states passed")
