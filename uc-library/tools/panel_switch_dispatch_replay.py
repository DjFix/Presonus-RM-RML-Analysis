"""Exact retained Switch dispatch replay; no event normalization."""
import argparse,hashlib,json,subprocess,time
from pathlib import Path
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--binary',type=Path,required=True);p.add_argument('--fixture',type=Path,required=True);p.add_argument('--out-root',type=Path,required=True);a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 meta=json.loads((a.fixture.parent/'validation.json').read_text());assert meta['passed'] and meta['cases']==44512 and sha(a.fixture)==meta['fixture_sha256']
 out=a.out_root/str(time.time_ns());out.mkdir(parents=True,exist_ok=False);count=0
 with (out/'stderr.log').open('w') as errors,(out/'results.jsonl').open('w') as result:
  child=subprocess.Popen([str(a.binary.resolve())],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=errors,text=True)
  try:
   for line in a.fixture.open():
    row=json.loads(line);child.stdin.write(row['command']+'\n');child.stdin.flush();actual=child.stdout.readline().strip();passed=actual==row['expected'];result.write(json.dumps(dict(index=count,role=row['role'],passed=passed,expected=row['expected'],actual=actual))+'\n');assert passed,(count,row,actual);count+=1
   child.stdin.write('quit\n');child.stdin.flush();assert child.stdout.readline().strip()=='OK' and child.wait(timeout=10)==0
  finally:
   if child.poll() is None:child.terminate();child.wait(timeout=10)
 assert count==44512
 (out/'validation.json').write_text(json.dumps(dict(passed=True,cases=count,fixture_sha256=sha(a.fixture),binary_sha256=sha(a.binary),results_sha256=sha(out/'results.jsonl'),replay_tool_sha256=sha(Path(__file__)),normalization=None,original_oracle_regenerated=False),indent=2)+'\n');print('PASS exact dispatch',count,out,flush=True)
if __name__=='__main__':main()
