"""Compare compiled production behavior with independent ARM observations."""
import argparse,json,subprocess,tempfile
from pathlib import Path
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'uc-library/tools/recovery/accept_worker.py').is_file())
def main():
 p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args()
 fixtures=json.loads(Path(a.fixtures).read_text())
 scratch=ROOT/'temp/recovery-work/large02-lifecycle-fix01/local';scratch.mkdir(parents=True,exist_ok=True)
 work=Path(tempfile.mkdtemp(prefix='native-replay-',dir=scratch));fresh=work/'native.json'
 subprocess.run([str(ROOT/'uc-library/.venv/bin/python'),str(Path(__file__).with_name('oracle.py')),'--out',str(fresh)],cwd=ROOT,check=True)
 assert json.loads(fresh.read_text())==fixtures,'native oracle observations changed'
 for i,case in enumerate(fixtures['cases']):
  result=subprocess.run([a.executable]+case['argv'],text=True,capture_output=True)
  assert result.returncode==0,(i,case['argv'],result.returncode,result.stdout,result.stderr)
  actual=json.loads(result.stdout)
  assert actual==case['expected'],(i,case['argv'],actual,case['expected'])
 subprocess.run([a.executable,'compat'],check=True,capture_output=True,text=True)
 print(json.dumps(dict(passed=True,cases=len(fixtures['cases']),native_regenerated=True,domain='normal initialized lifecycle; exact color/name/index lookup; Core source boundaries explicit; compatibility constructor excluded from original lifecycle credit')))
if __name__=='__main__':main()
