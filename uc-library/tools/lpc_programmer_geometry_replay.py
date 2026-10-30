"""Bounded native replay: no original ELF or device operations."""
import argparse
from pathlib import Path
import subprocess
p=argparse.ArgumentParser();p.add_argument('--executable',type=Path,required=True);p.add_argument('--fixtures',type=Path,required=True);a=p.parse_args();data=a.fixtures.read_text();rows=[list(map(int,x.split())) for x in data.splitlines()];assert len(rows)==8270 and all(len(x)==2 for x in rows);r=subprocess.run([str(a.executable)],input=data,capture_output=True,text=True);assert r.returncode==0,r.stderr;assert r.stderr=='PASS original_geometry_cases=8270\n';expected=sum(x[1]==0 for x in rows);assert r.stdout.count('[e] Unknown part id (')==expected==8246;print('PASS original_geometry_cases=8270 unknown_part_diagnostics=8246')
