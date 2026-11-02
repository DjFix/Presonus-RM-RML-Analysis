import argparse,json,subprocess
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixture',required=True);a=p.parse_args()
rows=json.load(open(a.fixture))
for case in rows:
 if 'input' in case:
  actual=int(subprocess.check_output([a.executable,case['method'],str(case['input'])],text=True))
  if actual!=case['result']:raise SystemExit(f'mismatch: {case} actual={actual}')
 else:
  if case['method']=='constructor':continue
  actual=json.loads(subprocess.check_output([a.executable,case['method'],str(case['flag'])],text=True))
  if actual['count']!=case['count'] or actual['trace']!=[t[0] for t in case['trace']]:raise SystemExit(f'trace/state mismatch: {case} actual={actual}')
  if case['method']=='load' and actual['result']!=case['result']:raise SystemExit('load result mismatch')
print(f'{sum(case.get('method') != 'constructor' for case in rows)} original ARM versus C++ cases passed; bounded simple/control methods; constructor excluded; control return registers excluded except load')
