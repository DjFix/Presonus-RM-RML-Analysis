"""Offline command/info replay; raw serial/clock imports are forbidden before execution."""
import argparse,hashlib,json,os,subprocess,uuid
from pathlib import Path
p=argparse.ArgumentParser()
for n in ['repository','executable','fixtures','work']:p.add_argument('--'+n,type=Path,required=True)
a=p.parse_args();r=a.repository.resolve();parent=a.work.resolve();assert parent.is_relative_to(r/'temp/test-work');parent.mkdir(parents=True,exist_ok=True);out=parent/('command-info-'+uuid.uuid4().hex);out.mkdir();tmp=out/'tmp';tmp.mkdir();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
undefined=subprocess.run(['nm','--undefined-only',a.executable],capture_output=True,text=True,check=True).stdout
assert not {'read','__read_chk','write','__write_chk','clock_gettime'}&{x.split()[-1].split('@')[0] for x in undefined.splitlines() if x.split()}
defined=subprocess.run(['nm','--defined-only',a.executable],capture_output=True,text=True,check=True).stdout
assert {'__wrap_read','__wrap___read_chk','__wrap_write','__wrap_clock_gettime'}<={x.split()[-1] for x in defined.splitlines() if x.split()}
data=a.fixtures.read_text();assert len(data.splitlines())==540;command=[str(a.executable.resolve())];env={**os.environ,'TMPDIR':str(tmp),'TMP':str(tmp),'TEMP':str(tmp),'ASAN_OPTIONS':'detect_leaks=1:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1'}
v=subprocess.run(command,input=data,capture_output=True,text=True,env=env,cwd=r)
(out/'native.stdout').write_text(v.stdout);(out/'native.stderr').write_text(v.stderr)
assert v.returncode==0,v.stderr
assert v.stdout=='PASS staged_command_info_cases=540\n'
(out/'validation.json').write_text(json.dumps({'passed':True,'cases':540,'command':command,'exe_sha256':sha(a.executable),'fixture_sha256':sha(a.fixtures),'all_serial_read_write_clock_calls_captured':True,'stdout_sha256':sha(out/'native.stdout'),'stderr_sha256':sha(out/'native.stderr')},indent=2)+'\n');print(v.stdout.strip())
