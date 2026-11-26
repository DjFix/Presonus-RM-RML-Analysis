import argparse, hashlib, importlib.util, json, subprocess
from pathlib import Path
from native import collect
import unicorn, elftools, sys
ROOT=Path(__file__).resolve().parents[4];BASE=Path(__file__).resolve().parent
CORE=Path('/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/sdk/lib')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--generate',action='store_true');ap.add_argument('--phase',choices=['all','compile','symbols','replay'],default='all');ap.add_argument('--exe');ap.add_argument('--fixtures');args=ap.parse_args();out=ROOT/args.out;out.mkdir(parents=True,exist_ok=True);commands=[]
 def run(argv):
  argv=list(map(str,argv));r=subprocess.run(argv,cwd=ROOT,text=True,capture_output=True);commands.append(dict(argv=argv,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr));(out/'commands.json').write_text(json.dumps(commands,indent=2));assert r.returncode==0,(argv,r.stdout,r.stderr);return r.stdout
 paths=[ROOT/'uc-library/include/presonus/panel/PresetNameCache.hpp',ROOT/'uc-library/include/presonus/panel/PresetNameManager.hpp',ROOT/'uc-library/src/Presonus/Panel/PresetNameCache.cpp',ROOT/'uc-library/src/Presonus/Panel/PresetNameManager.cpp',BASE/'Replay.cpp']
 fmt=ROOT/'uc-library/.venv/bin/clang-format';version=run([fmt,'--version']).strip();run([fmt,'--style=file','--fallback-style=LLVM','--dry-run','--Werror',*paths])
 compiler_version=run(['/usr/bin/c++','--version']).splitlines()[0]
 common=['/usr/bin/c++','-std=c++17','-Ulinux','-DCORE_USE_OPENSSL=1','-pthread','-I'+str(ROOT/'uc-library/include'),'-I'+str(ROOT/'third_party/ccl-framework')]
 dependencies=run([*common,'-M',*paths[2:4],BASE/'Replay.cpp'])
 (out/'dependencies.txt').write_text(dependencies)
 provider_hashes={}
 for token in dependencies.replace('\\\n',' ').split():
  p=Path(token)
  if p.is_absolute() and p.is_file() and p.is_relative_to(ROOT/'third_party/ccl-framework'):
   provider_hashes[str(p.relative_to(ROOT))]=sha(p)
 archives=[CORE/'libcorelib.a',CORE/'libpresonus_core_allocator.a'];before={str(p):sha(p) for p in archives}
 objects=[out/'PresetNameCache.o',out/'PresetNameManager.o'];exe=Path(args.exe).resolve() if args.exe else out/'Replay'
 if args.phase in ['all','compile']:
  for p,o in zip(paths[2:4],objects):run([*common,'-c',p,'-o',o])
  run([*common,BASE/'Replay.cpp',*objects,'-Wl,--start-group',*archives,'-Wl,--end-group','-ldl','-lrt','-o',exe])
  if args.phase=='compile':print('compile passed');return
 symbols=run(['/usr/bin/nm','--defined-only',exe]);(out/'symbols.txt').write_text(symbols)
 fixtures=Path(args.fixtures).resolve() if args.fixtures else BASE/'fixtures.json'
 if args.phase=='symbols':
  for o in json.loads(fixtures.read_text())['ranges']:assert o['mangled'] in symbols,o['mangled']
  print('symbols passed');return
 native=collect(exe)
 for o in native['ranges']:assert o['mangled'] in symbols,o['mangled']
 if args.generate:(BASE/'fixtures.json').write_text(json.dumps(native,indent=2)+'\n')
 else:assert json.loads(fixtures.read_text())==native
 process=subprocess.Popen([str(exe)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,cwd=ROOT)
 portable=[]
 def query(s):
  process.stdin.write(s+'\n');process.stdin.flush();line=process.stdout.readline();assert line,(s,process.poll(),process.stderr.read());return line.rstrip('\n')
 for case in native['cases']:
  i=case['inputs'];op=case['kind'];line=op+' '+(str(i['slots'])+' '+i['name'].encode().hex() if op=='cache' else (i['name'].encode().hex() or '-') if op=='empty' else str(i['count']) if op=='manager' else '')
  result=query(line);assert result==case['result'],(line,result,case['result']);portable.append(dict(command=line,result=result))
 portable.append(dict(command='regression',result=query('regression')));assert query('quit')=='0 0';process.stdin.close();assert process.wait(timeout=10)==0
 assert before=={str(p):sha(p) for p in archives}
 proof=dict(version=1,status='passed',ranges=native['ranges'],app_dependencies=native['app_dependencies'],native_cases=len(native['cases'])+len(native['lifecycle']),portable_cases=len(portable),portable=portable,formatter_version=version,compiler_version=compiler_version,oracle_versions=dict(python=sys.version,unicorn=unicorn.__version__,pyelftools=elftools.__version__),provider_source_hashes=provider_hashes,source_hashes={str(p.relative_to(ROOT)):sha(p) for p in paths},fixtures_sha256=sha(fixtures),native_producer_sha256=sha(BASE/'native.py'),replay_producer_sha256=sha(BASE/'check.py'),commands_sha256=sha(out/'commands.json'),symbols_sha256=sha(out/'symbols.txt'),provider_archives=before,pinned_core_commit='e8cbdea4a4a20e15111f5a690798a259c0374b31',domain=native['domain'],limitations=['Original ordinary returns, full declarations/layout/ARM ABI remain unresolved.','Source-port initialized entries express native capacity-indexed backing storage; convenience constructor retains requested slot count.','Injected caches remain borrowed intentionally; native registrations are owned. Allocation failure is exception-safe source-port adaptation rather than native leak.','Original constructor starts without observers; opaque registrations require injected sink or explicit typed receiver, never silent provider success.','No exception-unwinding/OOM/native negative indexing/hardware verification.'])
 (out/'proof.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(dict(status='passed',native_cases=proof['native_cases'],portable_cases=proof['portable_cases'])))
if __name__=='__main__':main()
