#!/usr/bin/env python3
import argparse, hashlib, json, pathlib, subprocess, time, datetime
BASE=pathlib.Path(__file__).resolve().parent
ROOT=BASE.parents[2]
SCRATCH=ROOT/'temp/recovery-work/graph-live-trial-05/item-worker'
SOURCES=['uc-library/include/presonus/MeterManagerBase.hpp','uc-library/src/Presonus/MeterManagerBase.cpp','uc-library/tests/graph_trial05_item_tests.cpp']
def run(argv):
    start=datetime.datetime.now(datetime.timezone.utc).isoformat(); t=time.monotonic()
    p=subprocess.run(argv,cwd=ROOT,text=True,capture_output=True)
    log={'start':start,'duration_seconds':time.monotonic()-t,'argv':list(map(str,argv)),'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
    with (SCRATCH/'checks.jsonl').open('a') as f:f.write(json.dumps(log)+'\n')
    if p.returncode: raise RuntimeError(json.dumps(log))
    return p.stdout

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('kind',choices=['format','compile','symbols','replay']);ap.add_argument('--executable');ap.add_argument('--fixtures',default=str(BASE/'native-fixtures.json')); args=ap.parse_args()
    SCRATCH.mkdir(parents=True,exist_ok=True)
    exe=pathlib.Path(args.executable) if args.executable else SCRATCH/'graph_trial05_item_tests'
    if args.kind=='format':
        print(run(['uc-library/.venv/bin/clang-format','--version']).strip())
        run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror']+SOURCES)
    elif args.kind=='compile':
        flags=['/usr/bin/c++','-std=c++17','-DCORE_USE_OPENSSL=1','-DNDEBUG=1','-DPRESONUS_HAS_UPSTREAM_CORE=1','-Iuc-library/include','-Ithird_party/ccl-framework','-O2','-fno-lto','-frtti','-pthread','-Ulinux']
        objects=[]
        for i,source in enumerate(SOURCES[1:]):
            obj=SCRATCH/f'{i}.o';run(flags+['-MMD','-MF',str(SCRATCH/f'{i}.d'),'-c',source,'-o',str(obj)]);objects.append(str(obj))
        run(['/usr/bin/c++','-pthread']+objects+['temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a','-ldl','-o',str(exe)])
    elif args.kind=='symbols':
        symbols=run(['/usr/bin/nm','--defined-only',str(SCRATCH/'0.o')]); originals=[]
        for i in range(1,6):
            packet=ROOT/f'temp/recovery-work/graph-live-trial-05/trial05_item_{i}-packet/context.json';j=json.loads(packet.read_text())
            original=j['originals'][0]['original']['mangled'];assert original in symbols,original; originals.append(original)
        print(json.dumps({'matched_originals':originals,'format':'ELF; no decoration'}))
    else:
        fixture=json.loads(pathlib.Path(args.fixtures).read_text()); cases=fixture['cases']
        t=time.monotonic();p=subprocess.run([str(exe)],input='\n'.join(c['input'] for c in cases)+'\n',text=True,capture_output=True,timeout=60)
        assert p.returncode==0,p.stderr
        lines=p.stdout.splitlines(); assert len(lines)==len(cases),(len(lines),len(cases))
        for i,(line,case) in enumerate(zip(lines,cases)):
            actual=json.loads(line);assert actual==case['observed'],(i,case['input'],actual,case['observed'])
        print(json.dumps({'passed':len(cases),'per_method':{i:sum(c['method']==i for c in cases) for i in range(1,6)},'duration_seconds':time.monotonic()-t,'executable':str(exe),'executable_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'fixture_sha256':hashlib.sha256(pathlib.Path(args.fixtures).read_bytes()).hexdigest()}))
if __name__=='__main__':main()
