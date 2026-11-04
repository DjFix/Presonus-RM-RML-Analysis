"""Compare actual source-port constructors to independent original ARM observations."""
import argparse,json,subprocess,tempfile
from pathlib import Path
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'uc-library/tools/recovery/accept_worker.py').is_file())
def main():
 p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args()
 fixture=json.loads(Path(a.fixtures).read_text());scratch=ROOT/'temp/recovery-work/large02_net_adapter01/local';scratch.mkdir(parents=True,exist_ok=True)
 fresh=Path(tempfile.mkdtemp(prefix='oracle-',dir=scratch))/'fixtures.json'
 subprocess.run([str(ROOT/'uc-library/.venv/bin/python'),str(Path(__file__).with_name('oracle.py')),'--out',str(fresh)],cwd=ROOT,check=True)
 assert json.loads(fresh.read_text())==fixture,'fresh original observations differ'
 for i,case in enumerate(fixture['cases']):
  result=subprocess.run([a.executable]+case['argv'],text=True,capture_output=True,check=True)
  assert json.loads(result.stdout)==case['expected'],(i,result.stdout,case['expected'])
 result=subprocess.run([a.executable,'singleton'],text=True,capture_output=True,check=True)
 assert json.loads(result.stdout)==fixture['cases'][0]['expected']
 result=subprocess.run([a.executable,'borrowed'],text=True,capture_output=True,check=True)
 assert json.loads(result.stdout)==dict(borrowed_preserved=True)
 print(json.dumps(dict(passed=True,cases=len(fixture['cases']),native_regenerated=True,source_compatibility=['borrowed','actual_CCL_StaticSingleton','owned_state_deallocation'],network_access=0)))
if __name__=='__main__':main()
