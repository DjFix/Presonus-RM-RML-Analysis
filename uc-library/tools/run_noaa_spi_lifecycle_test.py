"""Linux CTest driver: measure this test ELF's actual ctor allocation range."""
import subprocess,sys
from pathlib import Path
binary=Path(sys.argv[1]).resolve();fixture=Path(sys.argv[2]).resolve()
rows=subprocess.check_output(['nm','-S','--defined-only',str(binary)],text=True).splitlines()
matches=[r.split() for r in rows if r.split() and r.split()[-1]=='_ZN8Presonus4NOAA8TCardSPIC1Ev']
assert len(matches)==1 and len(matches[0])==4
size=int(matches[0][1],16);assert size>0
raise SystemExit(subprocess.run([str(binary),str(fixture),str(size)]).returncode)
