import json,subprocess,sys
cases=json.load(open(sys.argv[2]))['cases']
inputs=''
expected=[]
for c in cases:
 if c['kind']=='cache':values=[c['count'],c['index'],c['error'],*c['items']]
 elif c['kind']=='geq':values=[c['geq'],c['main_count'],c['aux_count'],c['geq_count'],c['error'],*c['main_items'],*c['aux_items'],c['result']]
 else:values=[c['dirty'],c['descriptor'],c['width'],len(c['controls']),*c['controls']]
 inputs+=c['kind']+' '+' '.join(map(str,values))+'\n'
 if c['kind']!='spi':
  expected.append([c['result']]);assert not c['writes']
  if c['kind']=='cache':assert len(c['error_reads'])==(not (0<=c['index']<c['count']))
  for r in c['error_reads']:assert r['value']==c['error']
 else:
  call=c['calls'][0] if c['calls'] else dict(descriptor=0,request=0,length=0)
  expected.append([c['dirty_after'],*c['tx'],*c['rx'],len(c['calls']),call['descriptor'],call['request'],call['length']])
p=subprocess.run([sys.argv[1]],input=inputs,text=True,capture_output=True,check=True)
observed=[list(map(int,line.split())) for line in p.stdout.splitlines()]
assert len(observed)==len(expected)
for i,(a,b) in enumerate(zip(observed,expected)):
 assert a==b,(i,cases[i],a,b)
print('PASS',len(cases),'panel cases: cache/Geq native sentinel reads; SPI original callee, dirty-state writes, tx/rx bytes, ioctl descriptor/request/length; no hardware')
