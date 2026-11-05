import sys,json,pathlib,subprocess,hashlib
p=pathlib.Path(sys.argv[2]);raw=p.read_bytes()
if len(sys.argv)>3: assert hashlib.sha256(raw).hexdigest()==sys.argv[3]
rows=[]
for c in json.loads(raw):
 rows.append(' '.join(map(str,[c['flag'],c['queue'],c['last'],c['received'],c['expected_flag'],c['expected_last'],c['expected_byte'],c['remaining'],c['clock_count'],len(c['posts']),*c['clocks'],*c['posts'],*[v for row in c['poststates'] for v in row]])))
subprocess.run([sys.argv[1]],input='\n'.join(rows)+'\n',text=True,check=True)
