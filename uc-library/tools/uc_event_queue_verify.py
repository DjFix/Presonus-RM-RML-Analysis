"""Compile and seal bounded original queue coalescing with external lock contract."""
import sys,json,struct,hashlib,subprocess,shutil,argparse,datetime,re
from pathlib import Path
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('repository',type=Path);p.add_argument('--formatter',type=Path,required=True);a=p.parse_args()
 repo=a.repository.resolve();lib=repo/'uc-library';target=lib/'validation/uc-event-queue'
 oracle=json.loads((target/'oracle.json').read_text());vectors=target/'arm-vectors.bin'
 assert sha(vectors)==oracle['vectors_sha256'] and vectors.stat().st_size>=12+(40+5*1216+4)*oracle['records']
 assert vectors.read_bytes()[:12]==b'UCQUv001'+struct.pack('<I',oracle['records'])
 for original in oracle['originals']:
  manifest=json.loads((lib/'recovered'/original['role']/'manifest.json').read_text());assert sha(repo/manifest['path'])==original['original_elf_sha256']
 run=target/'runs'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');run.mkdir(parents=True,exist_ok=False)
 def command(args,name):
  args=list(map(str,args));r=subprocess.run(args,cwd=lib,text=True,capture_output=True);(run/name).write_text('COMMAND: '+json.dumps(args)+'\n'+r.stdout+r.stderr)
  if r.returncode:print(r.stdout+r.stderr,flush=True)
  r.check_returncode();return r.stdout
 source='src/Presonus/UC/event_queue.cpp';header='include/presonus/uc/event_queue.hpp';test='tests/uc_event_queue_tests.cpp';scoped=[source,header,test]
 formatter=command([a.formatter,'--version'],'formatter.log').strip();assert '23.1.3' in formatter
 command([a.formatter,'--style=file:'+str(repo/'.clang-format'),'-i',*scoped],'format-apply.log')
 command([a.formatter,'--style=file:'+str(repo/'.clang-format'),'--dry-run','--Werror',*scoped],'format-check.log')
 formatting=dict(formatter=formatter,configuration_sha256=sha(repo/'.clang-format'),format_check_passed=True,files={x:sha(lib/x) for x in scoped})
 (run/'formatting.json').write_text(json.dumps(formatting,indent=2)+'\n')
 closure=set(scoped);pending=list(scoped)
 while pending:
  file=lib/pending.pop()
  for inc in re.findall(r'^#include\s+"([^"]+)"',file.read_text(),re.M):
   name='include/'+inc;path=lib/name;assert path.is_file(),name
   if name not in closure:closure.add(name);pending.append(name)
 sources=sorted(closure|{'tools/core_uc_oracle.py','tools/uc_event_queue_oracle.py','tools/uc_event_queue_verify.py'})
 hashes={x:sha(lib/x) for x in sources};obj=run/'event_queue.o';exe=run/'uc_event_queue_tests'
 flags=['g++','-std=c++17','-O2','-Wall','-Wextra','-Wpedantic','-Iinclude']
 command([*flags,'-c',source,'-o',obj],'compile.log');command([*flags,test,obj,'-o',exe],'test-build.log')
 output=command([exe,vectors],'tests.log');assert f"{oracle['records']} original ARM EventQueue fixtures passed" in output
 assert '1 portable RAII exception cleanup check passed (ARM unwind unverified)' in output
 nm=command(['nm','--defined-only',obj],'symbols.log');defined={line.split()[-1] for line in nm.splitlines() if line.split()}
 expected={s['mangled'] for original in oracle['originals'] for s in original['functions']};assert expected<=defined,expected-defined
 assert hashes=={x:sha(lib/x) for x in sources}
 evidence=repo/'evidence/recovery/2026-10-26/uc-event-queue'/run.name
 proof=dict(namespace='Presonus::UC',classes=['EventQueue'],originals=oracle['originals'],sources=hashes,mangled_names=sorted(expected),compiled_mangled_names_matched=True,cpp_differential_passed=True,records=oracle['records'],cases=oracle['cases'],domain=oracle['domain'],external_dependencies=oracle['dependencies'],declaration_uncertainties=oracle['limitations'],formatting_reference=formatting,vectors_sha256=sha(vectors),object_sha256=sha(obj),test_binary_sha256=sha(exe),compiler=command(['g++','--version'],'compiler.log').splitlines()[0],test_output=output,original_arm_object_layout_compatible=False,original_function_fully_verified=False,hardware_verified=False,run_directory=str(run.relative_to(lib)),evidence_directory=str(evidence.relative_to(repo)))
 proof['fixture_format']=oracle['vector_format']
 proofpath=target/'validation.json';proofpath.write_text(json.dumps(proof,indent=2)+'\n')
 ready=[]
 for original in oracle['originals']:
  for symbol in original['functions']:
   ready.append(dict(mangled=symbol['mangled'],original_elf_sha256=original['original_elf_sha256'],original_address=symbol['address'],validation='validation/uc-event-queue/validation.json',validation_sha256=sha(proofpath),sources=hashes,portable_ready=True,domain=oracle['domain'],original_return_declaration_proven='6updateI' in symbol['mangled']))
 (target/'ready-functions.fragment.json').write_text(json.dumps(dict(functions=ready),indent=2)+'\n')
 for name in ['validation.json','ready-functions.fragment.json']:shutil.copyfile(target/name,run/name)
 evidence.mkdir(parents=True,exist_ok=False)
 for name in sources:
  dest=evidence/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(lib/name,dest)
 for name in ['oracle.json','arm-vectors.bin','validation.json','ready-functions.fragment.json']:shutil.copyfile(target/name,evidence/name)
 shutil.copytree(run,evidence/'run');shutil.copyfile(repo/'temp/uc-event-queue/oracle-01/log.txt',evidence/'oracle.log')
 for previous in sorted((target/'runs').iterdir()):
  if previous!=run and not (previous/'validation.json').exists():shutil.copytree(previous,evidence/'failed-replays'/previous.name)
 files=[x for x in sorted(evidence.rglob('*')) if x.is_file()];(evidence/'SHA256SUMS').write_text(''.join(sha(x)+'  '+str(x.relative_to(evidence))+'\n' for x in files))
 print(output,end='');print('PASS:',len(expected),'mangles;',len(ready),'ELFentries;',evidence.relative_to(repo))
if __name__=='__main__':main()
