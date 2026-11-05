#!/usr/bin/env python3
import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--object',default='temp/recovery-work/network-setup-settings/NetworkSetupComponent.o');a=p.parse_args()
result=subprocess.run(['nm','--defined-only',a.object],text=True,capture_output=True,check=True);names={line.split()[-1] for line in result.stdout.splitlines() if line.split()}
base=Path('temp/recovery-work/rolling200-02/implementation-plan01/packets-isolated-network_setup02/packets');found=[]
for packet in sorted(base.iterdir()):
 r=json.loads((packet/'request.json').read_text());sym=r['targets'][0]['mangled'];assert sym in names,sym;found.append(sym)
print(json.dumps({'passed':True,'format':'ELF x86_64; no Mach-O decoration','symbols':found,'limitation':'Encoded interface match only; ordinary returns/layout/ARM ABI unresolved'}))
