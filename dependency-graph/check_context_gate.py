"""End-to-end context gate checks; only recovery scratch packets are written."""
import json
import pathlib
import shutil
import subprocess
import time

ROOT=pathlib.Path(__file__).resolve().parents[1]
PY=ROOT/'uc-library/.venv/bin/python'
CLI=ROOT/'uc-library/tools/recovery/select_context.py'
OUT=ROOT/'temp/test-work/context-gate-e2e'/str(time.time_ns())
OUT.mkdir(parents=True,exist_ok=False)
receipts=[]


def call(name,args,success=True):
    start=time.perf_counter()
    result=subprocess.run([str(PY),str(CLI),*args],cwd=ROOT,capture_output=True,text=True)
    (OUT/(name+'.log')).write_text(result.stdout+result.stderr)
    receipts.append({'name':name,'argv':[str(PY),str(CLI),*args],
                     'returncode':result.returncode,'seconds':time.perf_counter()-start})
    assert (result.returncode==0)==success,(name,result.stdout,result.stderr)


packet='temp/recovery-work/context-gate/packet-03'
call('valid-packet',['validate','--packet',packet])
task=json.loads((ROOT/'dependency-graph/tasks/control-registrar-audit.json').read_text())
task['task_id']='control_registrar_context_audit_peer'
task_path=OUT/'peer-task.json';task_path.write_text(json.dumps(task,indent=2)+'\n')
peer='temp/recovery-work/context-gate/packet-peer-01'
call('prepare-peer',['prepare','--task',str(task_path.relative_to(ROOT)),'--out',peer])
call('independent-batch',['batch-dispatch','--packets',packet,peer,'--out','temp/recovery-work/context-gate/batch-01'])
tampered=OUT/'tampered';shutil.copytree(ROOT/packet,tampered)
with (tampered/'CONTEXT.md').open('a') as stream:stream.write('\nUnbound packet edit\n')
call('reject-tamper',['validate','--packet',str(tampered.relative_to(ROOT))],success=False)
invalid=dict(task,task_id='invalid_namespace',namespace='Presonus::Panel::ControlRegistrarFake')
invalid_path=OUT/'invalid-namespace.json';invalid_path.write_text(json.dumps(invalid))
call('reject-namespace',['prepare','--task',str(invalid_path.relative_to(ROOT)),
                         '--out','temp/recovery-work/context-gate/invalid-namespace-01'],success=False)
fake=[]
for name,owned,read in [('conflict_a',['uc-library/src/example.cpp'],{}),
                        ('conflict_b',['uc-library/src/other.cpp'],{'uc-library/src/example.cpp':'x'})]:
    path=OUT/name;path.mkdir();fake.append(str(path.relative_to(ROOT)))
    (path/'context.json').write_text(json.dumps({'task_id':name,'generation_sha256':'same','selected_file_sha256':read}))
    (path/'request.json').write_text(json.dumps({'owned_files':owned}))
call('reject-dependent-batch',['batch-dispatch','--packets',*fake,
                               '--out','temp/recovery-work/context-gate/rejected-batch-01'],success=False)
call('baseline-expansion',['expand','--packet',packet,'--query','callees',
                           '--seed','function:_ZNK8Presonus5Panel16ControlRegistrar2atEi',
                           '--reason','End-to-end baseline expansion regression','--baseline',
                           '--out','temp/recovery-work/context-gate/expansion-02'])
expanded=json.loads((ROOT/'temp/recovery-work/context-gate/expansion-02/expansion.json').read_text())
assert len(expanded['nodes'])==3
(OUT/'results.json').write_text(json.dumps({'passed':True,'receipts':receipts,
      'expansion_nodes':len(expanded['nodes']),'canonical_registry_mutated':False},indent=2)+'\n')
print(json.dumps({'passed':True,'checks':len(receipts),'evidence':str(OUT)}))
