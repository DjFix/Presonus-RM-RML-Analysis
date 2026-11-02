import argparse,hashlib,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args()
out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
subprocess.run(['uc-library/.venv/bin/python','uc-library/tests/recovery/trial07/surfacenet/native.py','--out',str(out)],check=True)
if out.read_bytes()!=Path(a.fixtures).read_bytes():raise SystemExit('fresh native fixture mismatch')
print('fresh original ARM fixtures verified',hashlib.sha256(out.read_bytes()).hexdigest())
