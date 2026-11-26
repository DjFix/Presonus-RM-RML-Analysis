"""Attributed canonical GR7 exact-read successor; original worker inputs unchanged."""
from pathlib import Path
import argparse,datetime,hashlib,json,os,shlex,subprocess,sys,tempfile

def digest(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def binding(p):return {'path':str(p),'sha256':digest(p)}
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--task',required=True);parser.add_argument('--exe',type=Path,required=True);parser.add_argument('--read-transition',type=Path,required=True);parser.add_argument('--read-transition-sha256',required=True);a=parser.parse_args()
    root=Path.cwd().resolve();build=root/'temp/core-upstream/root-integration-01';transition=a.read_transition.resolve();assert transition.is_relative_to(root) and digest(transition)==a.read_transition_sha256;doc=json.loads(transition.read_text());assert a.task in doc['contexts']
    checker=root/'uc-library/tests/recovery/sqlite_grfive_24f6e99aab28/check_current67.py';exe=a.exe.resolve();assert exe.parent==build and exe.is_file();outroot=root/'temp/test-work/current67-gr-read-successors';outroot.mkdir(parents=True,exist_ok=True);stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');dest=Path(tempfile.mkdtemp(prefix=a.task+'-'+stamp+'-'+str(os.getpid())+'-',dir=outroot))
    table=build/'compile_commands.json';before={};records=[];rows=json.loads(table.read_text())
    def bind(p):
        p=p.resolve();h=digest(p);assert str(p) not in before or before[str(p)]==h;before[str(p)]=h;return {'path':str(p),'sha256':h}
    metadata={'compile_table':bind(table),'transition':bind(transition),'checker':bind(checker),'adapter':bind(Path(__file__).resolve()),'executable':bind(exe)}
    for i,name in enumerate(['MeterBallistics','MeterMaid','GRMeterMaid']):
        source=root/f'uc-library/src/Presonus/{name}.cpp';row,=[x for x in rows if Path(x['file'])==source and x['output'].startswith('CMakeFiles/presonus_common_objects.dir/')];obj=Path(row['directory'])/row['output'];dep=Path(str(obj)+'.d');assert obj.is_file() and dep.is_file();alias=dest/f'production{i}.o';alias.symlink_to(obj)
        dependencies={}
        for name2 in shlex.split(dep.read_text().replace('\\\n',' ').split(':',1)[1]):
            path=Path(name2);path=(path if path.is_absolute() else Path(row['directory'])/path).resolve();dependencies[str(path)]=bind(path)
        records.append({'source':bind(source),'object':bind(obj),'depfile':bind(dep),'compile_entry':row,'alias':str(alias),'dependencies':dependencies})
    driver_source=root/'uc-library/tests/recovery'/a.task/'Replay.cpp';driver,=[x for x in rows if Path(x['file'])==driver_source];parts=Path(driver['output']).parts;link=Path(driver['directory'])/parts[0]/parts[1]/'link.txt';tokens=shlex.split(link.read_text());output=Path(tokens[tokens.index('-o')+1]);output=(output if output.is_absolute() else Path(driver['directory'])/output).resolve();assert output==exe
    metadata['driver_source']=bind(driver_source);metadata['driver_object']=bind(Path(driver['directory'])/driver['output']);metadata['driver_compile_entry']=driver;metadata['link']=bind(link)
    archives=[]
    for token in tokens:
        if not token.endswith('.a'):continue
        path=Path(token);path=(path if path.is_absolute() else Path(driver['directory'])/path).resolve();archives.append(bind(path))
    assert any(Path(x['path']).name=='libpresonus_uc.a' for x in archives)
    context=root/doc['contexts'][a.task]['path'];assert digest(context)==doc['contexts'][a.task]['sha256'];metadata['original_context']=bind(context)
    for path,row in doc['read_transitions'].items():
        bind(root/path);bind(root/row['previous_frozen']['path']);bind(root/row['current_frozen']['path']);bind(root/row['accepted_current_source_owner_review']['path'])
    print('Canonical GR proof directory: '+str(dest),flush=True)
    argv=[sys.executable,'-B',str(checker),'replay','--task',a.task,'--exe',str(exe),'--no-consumers','--canonical-object-dir',str(dest),'--read-transition',str(transition),'--read-transition-sha256',a.read_transition_sha256]
    result=subprocess.run(argv,cwd=root)
    for path,h in before.items():assert digest(Path(path))==h,('Canonical input changed during replay',path)
    receipt={'task':a.task,'actual_argv':argv,'returncode':result.returncode,'current_canonical_metadata':metadata,'current_canonical_objects':records,'actual_link_archives':archives,'original_context_unchanged':True,'old_worker_proof_relabelled':False,'proof_directory':str(dest),'scope':'Actual canonical objects/read generations; original format/symbol/native/fixture/host checks retained. Separate18consumer/full/role/install/compile-once gates unchanged.'}
    (dest/'canonical-inputs-and-run.json').write_text(json.dumps(receipt,indent=2)+'\n')
    if result.returncode==0:assert (dest/'canonical-current67-replay.json').is_file()
    print('Canonical GR proof directory: '+str(dest)+'; returncode '+str(result.returncode),flush=True)
    raise SystemExit(result.returncode)
if __name__=='__main__':main()
