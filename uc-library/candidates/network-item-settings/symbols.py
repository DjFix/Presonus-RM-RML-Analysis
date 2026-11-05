#!/usr/bin/env python3
import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--object',default='temp/recovery-work/network-item-settings/NetworkSetupComponent.o');a=p.parse_args()
r=subprocess.run(['nm','--defined-only',a.object],text=True,capture_output=True,check=True);names={x.split()[-1] for x in r.stdout.splitlines() if x.split()};found=[]
base=Path('temp/recovery-work/rolling200-02/implementation-plan01/packets-current-network-items02/packets')
for i in (1,2):
 req=json.loads((base/f'rolling200_02_network_items_{i:02d}'/'request.json').read_text());s=req['targets'][0]['mangled'];assert s in names,s;found.append(s)
print(json.dumps({'passed':True,'symbols':found,'format':'Linux ELF x86_64 no object decoration','limitation':'encoded interfaces only; provisional return types not established by names'}))
