import argparse,json,pathlib,subprocess
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);p.add_argument('--work-dir',type=pathlib.Path);a=p.parse_args()
j=json.loads(pathlib.Path(a.fixtures).read_text());root=pathlib.Path(__file__).resolve().parents[5]
folder=a.work_dir if a.work_dir is not None else root/'temp/recovery-work/frontier-small01/frontier01_w01/provider-files';folder.mkdir(parents=True,exist_ok=True)
# Existing real CCL FileIterator sees these files; checks record rebuild notifications
# and path construction. No external hardware, network or user files are touched.
(folder/'01.Disk Preset.preset').write_text('fixture\n')
native_only=0;cases=0
for c in j['cases']:
 if c['packet']==1 and c['argument']==0xffffffff:native_only+=1;continue
 r=subprocess.run([a.executable,str(c['packet']),str(c['argument']),str(folder)],text=True,capture_output=True)
 assert r.returncode==0,(c['packet'],c['argument'],r.returncode,r.stdout,r.stderr)
 lines=r.stdout.splitlines();assert lines[-1]=='PROVIDER_OK';assert lines[:-1]==c['normalized'],(c,lines)
 cases+=1
print(cases,'portable caller traces match independent native traces; actual current CCL/app providers executed; provider assertions passed;',native_only,'native-only out-of-range slot case')
