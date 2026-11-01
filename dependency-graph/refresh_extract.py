"""Container worker: actual GCC replay followed by Clang AST for affected TUs."""
import concurrent.futures
import json
import pathlib
import sys
import shlex
import subprocess
from full_source_graph import extract
from gcc_source_graph import replay
from context_runtime import sha
from code_identity import normalize_ast


def canonical_inputs(inputs):
    result = {}
    for path, digest in inputs.items():
        canonical = str(pathlib.Path(path).resolve())
        if canonical in result and result[canonical] != digest:
            raise ValueError('Conflicting hashes for aliases of input: ' + canonical)
        result[canonical] = digest
    return result


def unit(owner, row, out):
    dest = out / 'observations' / owner.replace(':', '-')
    dest.mkdir(parents=True, exist_ok=False)
    scratch = dest / 'scratch'; scratch.mkdir()
    # Discover current includes before compilation, rather than trusting a
    # production depfile that predates the edits being indexed.
    argv = list(row.get('arguments') or shlex.split(row['command']))
    argv[argv.index('-o') + 1] = str(dest / 'dependency-only.o')
    depfile = dest / 'before.d'
    argv += ['-M', '-MF', str(depfile)]
    with (dest / 'dependencies.log').open('w') as log:
        result = subprocess.run(argv, cwd=row['directory'], stdout=log, stderr=subprocess.STDOUT)
    if result.returncode: raise ValueError('Dependency discovery failed: ' + owner)
    root = pathlib.Path(__file__).resolve().parents[1]
    paths = [str((pathlib.Path(row['directory']) / p).resolve()) for p in
             shlex.split(depfile.read_text().replace('\\\n', '').partition(': ')[2])]
    before = {p: sha(p) for p in paths if pathlib.Path(p).is_relative_to(root)}
    result = replay(0, row, scratch, dest)
    if not result['passed']: raise ValueError('GCC failed: ' + owner)
    observed = dict(row, gcc_validation=str(dest / '0000.json'))
    if not extract(observed, dest / 'ast.json'): raise ValueError('Clang failed: ' + owner)
    # Keep row identity stable: gcc_validation is evidence, not compile configuration.
    ast = json.loads((dest / 'ast.json').read_text())
    observed_inputs = canonical_inputs(ast['input_sha256'])
    if any(p not in before or digest != before[p] for p, digest in observed_inputs.items()):
        raise ValueError('Include set/bytes changed between dependency scan and AST: ' + owner)
    if any(not pathlib.Path(p).is_file() or sha(p) != digest for p, digest in before.items()):
        raise ValueError('Inputs changed during compiler replay: ' + owner)
    ast['input_sha256'] = before
    ast['external_inputs'] = sorted(p for p in paths if not pathlib.Path(p).is_relative_to(root))
    ast, _ = normalize_ast(root, row, ast)
    (dest / 'ast.json').write_text(json.dumps(ast) + '\n')
    return owner


if __name__ == '__main__':
    out = pathlib.Path(sys.argv[1]); selected = json.loads((out / 'units.json').read_text())
    with concurrent.futures.ProcessPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(unit, owner, row, out) for owner, row in selected]
        for future in concurrent.futures.as_completed(futures):
            with (out / 'extract-progress.jsonl').open('a') as log:
                log.write(json.dumps({'owner': future.result(), 'passed': True}) + '\n')
