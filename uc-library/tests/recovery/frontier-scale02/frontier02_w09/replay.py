import json,subprocess,sys
for case in json.load(open(sys.argv[2])):
 lines=subprocess.check_output([sys.argv[1],str(case['n']),str(case['mode'])],text=True).splitlines()
 calls=list(map(int,lines[0].split()));counts=list(map(int,lines[1].split()))
 assert calls==case['calls'],(calls,case)
 assert counts==[int(i not in calls) for i in range(4)],(counts,case)
print('12 native trace/provider removal cases passed')
