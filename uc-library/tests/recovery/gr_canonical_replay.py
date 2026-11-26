"""Run unchanged GR owner checks on actual canonical production object aliases."""
from pathlib import Path
from hashlib import sha256
import argparse,json,subprocess,sys
p=argparse.ArgumentParser();p.add_argument('--task',required=True);p.add_argument('--exe',type=Path,required=True);a=p.parse_args();root=Path.cwd();build=root/'temp/core-upstream/root-integration-01';sources=['src/Presonus/MeterBallistics.cpp','src/Presonus/MeterMaid.cpp','src/Presonus/GRMeterMaid.cpp'];commands=json.loads((build/'compile_commands.json').read_text());dest=root/'temp/recovery-work/gr-five-implementation01'/a.task;dest.mkdir(parents=True,exist_ok=True);records=[]
for i,source in enumerate(sources):
 rows=[x for x in commands if Path(x['file'])==root/'uc-library'/source and x['output'].startswith('CMakeFiles/presonus_common_objects.dir/')];row,=rows;obj=Path(row['directory'])/row['output'];assert obj.is_file();alias=dest/('production'+str(i)+'.o');h=sha256(obj.read_bytes()).hexdigest()
 if alias.exists():assert sha256(alias.read_bytes()).hexdigest()==h
 else:alias.symlink_to(obj)
 records.append({'actual_canonical_object':str(obj),'alias':str(alias),'sha256':h,'actual_compile_entry':row})
report=dest/'canonical-object-aliases.json';report.write_text(json.dumps({'objects':records,'scope':'Actual canonical objects, no worker compile/source freshness claim; unchanged owner exact symbols/D0delete/native/format/replay guards retained'},indent=2)+'\n')
checker=root/'uc-library/tests/recovery/sqlite_grfive_24f6e99aab28/check.py';r=subprocess.run([sys.executable,'-B',str(checker),'replay','--task',a.task,'--exe',str(a.exe.resolve()),'--no-consumers'],cwd=root)
for record in records:assert sha256(Path(record['actual_canonical_object']).read_bytes()).hexdigest()==record['sha256']
raise SystemExit(r.returncode)
