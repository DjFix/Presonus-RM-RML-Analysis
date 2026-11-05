import argparse,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);a=p.parse_args();symbols={s.split()[-1] for s in subprocess.check_output(['nm','--defined-only',a.executable],text=True).splitlines() if s.split()};expected=[]
for name in ['c11_01','c10_01','c10_03','c10_04','c10_02']:
 d=json.loads((ROOT/f'temp/recovery-work/rolling200-implementation01/packets-batch04/packets/rolling200_impl_{name}/request.json').read_text());expected.extend(x['original']['mangled'] for x in d['originals'])
for s in expected:assert s in symbols,s
print('PASS exact Linux ELF compiled symbols: '+', '.join(expected))
