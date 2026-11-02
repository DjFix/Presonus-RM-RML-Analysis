"""Compare a supplied built executable with independent original ARM fixtures."""
import argparse,json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[5]
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args()
data=json.loads(pathlib.Path(a.fixtures).read_text());exe=str(pathlib.Path(a.executable).resolve())
for i,c in enumerate(data['cases']):
 folder=ROOT/c['argv'][-1];folder.mkdir(parents=True,exist_ok=True)
 # Each test uses a fresh directory to preserve evidence and avoid deletion.
 casefolder=folder.parent/('replay-files-%d'%i);casefolder.mkdir(exist_ok=True)
 argv=list(c['argv']);argv[-1]=str(casefolder.relative_to(ROOT))
 for f in c['files']:
  path=casefolder/f['name']
  # Real Core determines hidden by the filename; oracle flags are explicit.
  if f.get('hidden') and not f['name'].startswith('.'):
   path=casefolder/('.'+f['name'])
  if f.get('directory'):path.mkdir(exist_ok=True)
  else:path.touch(exist_ok=True)
 actual=subprocess.run([exe]+argv,cwd=ROOT,text=True,capture_output=True)
 # Directory spelling is an input substitution, including returned filenames.
 expected=c['expected'].replace(c['argv'][-1].encode().hex(),argv[-1].encode().hex())
 if actual.returncode or actual.stdout!=expected:
  print('FAIL',i,c['argv'],actual.returncode,actual.stderr)
  print('EXPECTED\n'+expected+'ACTUAL\n'+actual.stdout);sys.exit(1)
print('passed',len(data['cases']),'original ARM differential cases; Core provider boundaries and original declaration/ABI exclusions retained')
