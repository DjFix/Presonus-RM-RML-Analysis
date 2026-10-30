"""Offline transport replay; raw serial/clock imports are forbidden before execution."""
import argparse,hashlib,json,os,subprocess,uuid
from pathlib import Path
p=argparse.ArgumentParser()
for n in ['repository','executable','fixtures','work']:p.add_argument('--'+n,type=Path,required=True)
a=p.parse_args();r=a.repository.resolve();parent=a.work.resolve();assert parent.is_relative_to(r/'temp/test-work');parent.mkdir(parents=True,exist_ok=True);out=parent/('transport-'+uuid.uuid4().hex);out.mkdir();tmp=out/'tmp';tmp.mkdir();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
undefined=subprocess.run(['nm','--undefined-only',a.executable],capture_output=True,text=True,check=True).stdout
assert not {'open','open64','__open_2','tcgetattr','tcsetattr','tcflush','write','__write_chk','close','_ZN4Core11DebugPrintfEPKcz'}&{x.split()[-1].split('@')[0] for x in undefined.splitlines() if x.split()}
defined=subprocess.run(['nm','--defined-only',a.executable],capture_output=True,text=True,check=True).stdout
assert {'__wrap_open','__wrap_tcgetattr','__wrap_tcsetattr','__wrap_tcflush','__wrap_cfmakeraw','__wrap_write','__wrap_close','__wrap__ZN4Core11DebugPrintfEPKcz'}<={x.split()[-1] for x in defined.splitlines() if x.split()}
data=a.fixtures.read_text();assert len(data.splitlines())==4698;command=[str(a.executable.resolve())];env={**os.environ,'TMPDIR':str(tmp),'TMP':str(tmp),'TEMP':str(tmp),'ASAN_OPTIONS':'detect_leaks=1:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1'}
v=subprocess.run(command,input=data,capture_output=True,text=True,env=env,cwd=r)
(out/'native.stdout').write_text(v.stdout);(out/'native.stderr').write_text(v.stderr)
assert v.returncode==0,v.stderr
assert v.stdout=='PASS transport_cases=4698\n'
(out/'validation.json').write_text(json.dumps({'passed':True,'cases':4698,'command':command,'exe_sha256':sha(a.executable),'fixture_sha256':sha(a.fixtures),'all_serial_configuration_write_close_debug_calls_captured':True,'stdout_sha256':sha(out/'native.stdout'),'stderr_sha256':sha(out/'native.stderr')},indent=2)+'\n');print(v.stdout.strip())
