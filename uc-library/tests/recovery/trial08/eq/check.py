"""Worker-local nonmutating-input compile/symbol checks; no shared build edits."""
import argparse,json,pathlib,subprocess,os
ROOT=pathlib.Path(__file__).resolve().parents[5]
SCRATCH=ROOT/'temp/recovery-work/graph-live-trial-08/eq-worker'
EXE=SCRATCH/'replay'
SOURCES=['uc-library/src/Presonus/EQControl.cpp','uc-library/include/presonus/mixer_dsp/EQControl.hpp','uc-library/tests/graph_trial08_eq_tests.cpp']
COMPILE=['/usr/bin/c++','-std=c++17','-fno-rtti','-Wno-multichar','-Iuc-library/include','-Ithird_party/ccl-framework',SOURCES[0],SOURCES[2],'temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a','-o',str(EXE.relative_to(ROOT))]
def run(argv):
 print(json.dumps(argv),flush=True);return subprocess.run(argv,cwd=ROOT,env={**os.environ,'TMPDIR':str(SCRATCH)},text=True,check=True,capture_output=True)
def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['compile','symbols']);a=p.parse_args()
 if a.mode=='compile':
  r=run(COMPILE);print(r.stdout);print(r.stderr)
 else:
  r=run(['/usr/bin/nm','--defined-only',str(EXE.relative_to(ROOT))]);defined={line.split()[-1] for line in r.stdout.splitlines() if line.split()}
  for i in range(1,11):
   j=json.loads((ROOT/f'temp/recovery-work/graph-live-trial-08/batch03/packets/trial08_eq_{i}/context.json').read_text());m=j['originals'][0]['original']['mangled'];assert m in defined,m;print(m)
  print('10 exact original ELF mangled names matched; host ELF no decoration; no ARM ABI claim')
if __name__=='__main__':main()
