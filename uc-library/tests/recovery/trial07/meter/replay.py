"""Compare canonical built MeterControl executable directly against original ARM fixtures."""
import argparse,json,struct,subprocess
from pathlib import Path

def bits(x):return struct.unpack('<I',struct.pack('<f',x))[0]
def wire(c):
 values=[c['target'],*c['size'],c['reverse'],c['immediate'],c['hide_peak'],c['interpolator'],c['primary'],c['peak_param'],*[bits(x) for x in c['values']],*c['dirty'],*c['peak_dirty'],bits(c['input']),*c['a'],*c['b'],*c['clip'],c['new_peak'],c['param_choice'],c['msg'],c['enabled'],bits(c['param_value'])]
 return ' '.join(map(str,values))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--executable',required=True);ap.add_argument('--fixtures',required=True);a=ap.parse_args()
 cases=json.loads(Path(a.fixtures).read_text())['cases']
 p=subprocess.run([a.executable],input='\n'.join(wire(x['case']) for x in cases)+'\n',text=True,capture_output=True,check=True)
 lines=p.stdout.splitlines();assert len(lines)==len(cases),(len(lines),len(cases),p.stderr)
 for i,(line,c) in enumerate(zip(lines,cases)):
  got=json.loads(line);want=c['observed']
  if got!=want:raise AssertionError(json.dumps({'index':i,'case':c['case'],'expected':want,'actual':got},indent=2))
 print('PASS',len(cases),'original ARM differential cases',json.dumps({str(t):sum(x['case']['target']==t for x in cases) for t in range(10)}))
if __name__=='__main__':main()
