"""Archive full-source graph evidence; no readiness admission or producer relabelling."""
import hashlib
import json
import pathlib
import shutil
import sqlite3
import subprocess
import tarfile

ROOT=pathlib.Path(__file__).resolve().parents[1]
BASE=ROOT/'dependency-graph'
RUN=BASE/'runs/full-01'
CORE=BASE/'runs/core-source-01'
OUT=ROOT/'evidence/recovery/2026-10-31/dependency-graph/stage-02'


def sha(path):
    return hashlib.file_digest(path.open('rb'),'sha256').hexdigest()


def main():
    OUT.mkdir(parents=True,exist_ok=False)
    active=json.loads((ROOT/'uc-library/validation/registry-sqlite/ACTIVE.json').read_text())
    assert sha(ROOT/active['database']['path'])==active['database']['sha256']
    assert subprocess.run(['git','diff','--check'],cwd=ROOT,capture_output=True).returncode==0
    tests=subprocess.run([str(ROOT/'uc-library/.venv/bin/python'),'-m','unittest','discover','-s',str(BASE),'-v'],
                         text=True,capture_output=True)
    (OUT/'unit-tests.log').write_text(tests.stdout+tests.stderr)
    assert tests.returncode==0
    checks=[json.loads((RUN/(b+'-full-check.json')).read_text()) for b in ('neo4j','memgraph')]
    assert checks[0]['identity_set_sha256']==checks[1]['identity_set_sha256']
    for b in ('neo4j','memgraph'):
        assert json.loads((CORE/(b+'-full-load.json')).read_text())['exact_counts_match']
    graph=sqlite3.connect((RUN/'graph.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
    assert not graph.execute('PRAGMA foreign_key_check').fetchall()
    for category,paths in (
        ('current-tool-sources',[p for p in BASE.iterdir() if p.is_file()]),
        ('main-results',[p for p in RUN.iterdir() if p.is_file() and p.suffix in ('.json','.md')]),
        ('core-results',[p for p in CORE.iterdir() if p.is_file() and p.suffix in ('.json','.md')]),
        ('docker-operations',list((BASE/'runs/docker-operations').iterdir())),
        ('frozen-main-extractors',list(RUN.glob('extractor-*.py'))),
        ('frozen-core-extractors',list(CORE.glob('extractor-*.py'))),
    ):
        destination=OUT/category;destination.mkdir()
        for path in paths:shutil.copy2(path,destination/path.name)
    packet=json.loads((RUN/'agent-context.json').read_text())
    selected=set(packet['source_files'])|{p.removeprefix('file:') for p in packet['fixtures']}
    for source in selected:
        destination=OUT/'case-inputs'/source
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/source,destination)
    # Compiler stdout/stderr and cgraphs remain exact input artifacts, not regenerated proofs.
    with tarfile.open(OUT/'compiler-logs-and-callgraphs.tar.gz','w:gz') as archive:
        for run in (RUN,CORE):
            directory=next(run.glob('gcc-all-*'))
            for proof_file in directory.glob('[0-9]*.json'):
                proof=json.loads(proof_file.read_text())
                for path in (proof_file,pathlib.Path(proof['dump']),pathlib.Path(proof['scratch'])/'compile.log'):
                    archive.add(path,arcname=str(path.relative_to(ROOT)))
    artifacts=[RUN/'graph.sqlite',RUN/'delta-nodes.csv',RUN/'delta-edges.csv',
               CORE/'qualified-nodes.csv',CORE/'qualified-edges.csv']
    manifest={'checkout_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
              'core_commit':subprocess.check_output(['git','-C',str(ROOT/'third_party/ccl-framework'),'rev-parse','HEAD'],text=True).strip(),
              'operational_registry_unchanged':True,'registry_sha256':active['database']['sha256'],
              'query_results_all_backends_equal':True,'foreign_keys_passed':True,'unit_tests_passed':True,
              'artifact_inventory':{str(p.relative_to(ROOT)):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in artifacts},
              'tool_source_snapshot_semantics':'Current review versions at seal; frozen AST workers are separate. Historical receipts keep their own producer hashes and are not relabelled as executions of current sources.',
              'runtime_callgraph_or_original_arm_abi_complete':False,
              'production_readiness_or_schema_changed':False}
    manifest['archived_files']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file()}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'evidence':str(OUT),'foreign_keys':True,'all_backends_equal':True,'registry_unchanged':True}))


if __name__=='__main__':main()
