import json,subprocess,sys
rows=json.load(open('uc-library/candidates/graph-live-trial-04-panel/fixtures.json'))
lines=subprocess.check_output([sys.argv[1]],text=True).splitlines();assert len(lines)==len(rows)
for row,line in zip(rows,lines):
 trace=''
 for name,args in row['trace']:
  a=b=0
  if name in ['controlAt','groupAt','findGroup','byTag','blink']:a=args[1]
  if name=='slot10':a,b=args[1:3]
  trace+=f'{name}:{a},{b};'
 expected=f"{row['method']} {row['count_or_tag']} {row['flag']} {trace}"
 assert line==expected,(line,expected)
print('50 independent ARM/C++ trace cases passed; dependency bodies stubbed')
