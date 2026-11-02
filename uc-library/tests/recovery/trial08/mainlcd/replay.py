"""Compare an explicit built executable with independently captured ARM fixtures."""
import argparse,json,subprocess
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--executable',required=True);ap.add_argument('--fixtures',required=True);args=ap.parse_args()
fixture=json.loads(Path(args.fixtures).read_text())
for case in fixture['cases']:
 i=case['inputs'];target=case['target'];o=case['observed']
 argv=[args.executable,*map(str,[target,i['lcd'],i['current'],i['modal'],i['back'],i['arg'],i['provider_editing'],i['lookup'],i['start_tag']])]
 output=subprocess.check_output(argv,text=True).split();result,lcd,observer=map(int,output[:3]);trace=output[3:]
 expected=[]
 for name,r0,r1 in o['trace']:
  value= r1 if name in ('getPageByTag','showPagePointer','stopTextInput') else r0 if name=='isEditing' else 0
  expected.append(f'{name}:{value}')
 assert trace==expected,(target,case['variant'],trace,expected)
 assert lcd==o['lcd'] and observer==o['observer'],(target,case['variant'],lcd,observer,o)
 if target in (1,2,3,9):assert result==o['r0'],(target,case['variant'],result,o['r0'])
print(f"{len(fixture['cases'])} original ARM boundary observations matched: returns where declared for port, state, observer side effect and ordered typed call arguments")
subprocess.run([args.executable,'--provider-smoke'],check=True)
