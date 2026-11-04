import argparse,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5]
def check(exe):
    symbols={line.split()[-1] for line in subprocess.check_output(['nm','--defined-only',str(exe)],text=True).splitlines() if line.split()}
    expected=[]
    for i in range(1,8):
        c=json.loads((ROOT/f'temp/recovery-work/reconstruction-200-01/large-batch01/packets/large01_w05_{i:02d}/context.json').read_text())
        expected.extend(o['original']['mangled'] for o in c['originals'])
    for symbol in expected:assert symbol in symbols,symbol
    print('PASS exact ELF names: '+', '.join(expected))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--executable',required=True);a=p.parse_args();check(a.executable)
