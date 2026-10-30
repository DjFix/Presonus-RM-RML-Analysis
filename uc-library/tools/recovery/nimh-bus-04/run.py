"""Retain per-attempt output, exact commands, source hashes and phase timings."""
from pathlib import Path
from datetime import datetime,timezone
import subprocess,sys,json,time,hashlib,shutil
ROOT=Path('/home/rs/projects/opencs/ai-line-analysis')
OP=ROOT/'uc-library/tools/recovery/nimh-bus-04'
OUT=ROOT/'evidence/recovery/2026-10-27/nimh-bus-04'
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
logdir=OUT/'attempts'/stamp;logdir.mkdir(parents=True)
for n in ['functional-audit.log','correlation.log','yosys-check.log']:
    if (OUT/n).exists():shutil.copyfile(OUT/n,logdir/('previous-'+n))
steps=json.loads((OUT/'commands.json').read_text()) if (OUT/'commands.json').exists() else []
for name in sys.argv[1:] or ['functional','correlate','counters','feedback','audit','yosys']:
    if name=='yosys':
        cmd=[str(ROOT/'temp/nimh-functional-tools/bin/yowasp-yosys'),'-Q','-T','-p',
             'read_verilog '+str(OUT/'functional-partial.v')+'; hierarchy -check -top nimh_partial; stat']
        timeout=120
    else:
        cmd=[str(ROOT/'temp/xmen-stm32-tools/bin/python'),str(OP/(name+'.py'))];timeout=300
    start=time.monotonic();record=dict(step=name,command=cmd,started_at=datetime.now(timezone.utc).isoformat(),run_id=stamp)
    if name=='yosys':record['verilog_sha256']=hashlib.sha256((OUT/'functional-partial.v').read_bytes()).hexdigest()
    with (logdir/(name+'.log')).open('w') as f:
        try:record['returncode']=subprocess.run(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=timeout).returncode
        except subprocess.TimeoutExpired:record['returncode']=None;record['timeout_seconds']=timeout
    record.update(finished_at=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-start,log=str((logdir/(name+'.log')).relative_to(ROOT)))
    steps.append(record)
    (OUT/'commands.json').write_text(json.dumps(steps,indent=2)+'\n')
    shutil.copyfile(logdir/(name+'.log'),OUT/(name+'.log'))
    print(name,record['returncode'],round(record['elapsed_seconds'],2),record['log'],flush=True)
    if record['returncode']!=0:sys.exit(1)
