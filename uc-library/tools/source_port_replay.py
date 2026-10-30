"""Replay retained source-port lines against an active root executable."""
import argparse
import gzip
from pathlib import Path
import subprocess
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--executable',type=Path,required=True)
p.add_argument('--fixtures',type=Path,required=True)
p.add_argument('--expected',type=Path,required=True)
p.add_argument('--cases',type=int,required=True)
p.add_argument('--argument',action='append',default=[])
a=p.parse_args()
def read(path):
    raw=path.read_bytes()
    return gzip.decompress(raw) if path.suffix=='.gz' else raw
stdin,expected=read(a.fixtures),read(a.expected)
assert len(stdin.splitlines())==len(expected.splitlines())==a.cases
r=subprocess.run([str(a.executable),*a.argument],input=stdin,capture_output=True)
assert r.returncode==0,r.stderr.decode(errors='replace')
assert r.stdout==expected,'Active source-port output differs from retained witness'
print(f'PASS {a.cases} retained source-port cases')
