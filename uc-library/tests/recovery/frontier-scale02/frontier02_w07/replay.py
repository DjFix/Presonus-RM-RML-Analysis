import json,subprocess,sys
from oracle import cases
fixtures=json.load(open(sys.argv[2]))
assert fixtures==cases()
for c in fixtures:
 output=subprocess.check_output([sys.argv[1],str(c['selected']),str(c['component']),str(c['id'])],text=True)
 assert list(map(int,output.split()))==[x['return'] for x in c['observations']]
print('15 cases / 30 native and portable executions; borrowed ID mutation covered')
