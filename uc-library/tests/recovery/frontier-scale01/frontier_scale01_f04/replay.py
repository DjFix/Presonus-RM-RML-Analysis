import json,subprocess,sys
from pathlib import Path
from oracle import observe
f=json.loads(Path(sys.argv[2]).read_text()); native=observe()
assert f==native, "fixture differs from fresh native execution"
cases=[c for r in f["originals"] for c in r["observations"]]
p=subprocess.run([sys.argv[1]],input="".join(str(c["input_word"])+"\n" for c in cases),capture_output=True,text=True,check=True)
assert [int(x) for x in p.stdout.split()]==[c["r0"] for c in cases]
print(json.dumps({"cases":len(cases),"originals":2,"domain":"six opaque 32-bit address tokens per original, repeated const access, native object preserved, SP/FP restored, stack writes traced; no external calls"}))
