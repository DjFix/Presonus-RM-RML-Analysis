"""Verify one finished compiler capture before making per-owner reference links.

producer_bindings = {"producers": {repo_relative_path: current_sha256, ...},
 "source_metadata": {"plan.json": trusted_sha256, "units.json": trusted_sha256,
                     "extract.json": trusted_sha256}}
Metadata hashes must come from the caller's retained capture binding. Returned
AST/GCC hashes are fresh observations, never invented historical execution seals.
No graph, registration, staging facts, operational index or compiler is touched.
"""
import ast
import hashlib
import json
from pathlib import Path
import re
import shlex

from code_identity import VERSION, context_descriptor

EXTRACTORS = ('refresh_extract', 'full_source_graph', 'gcc_source_graph', 'code_identity')
METADATA = ('plan.json', 'units.json', 'extract.json')


def _sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _inside(root, value, *, regular=False):
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    if not path.is_relative_to(root) or '..' in path.parts:
        raise ValueError('Path traversal or non-project path: ' + str(path))
    for part in path.relative_to(root).parents:
        if (root / part).is_symlink():
            raise ValueError('Reference path traverses a symlink: ' + str(path))
    if path.is_symlink() or not path.resolve().is_relative_to(root):
        raise ValueError('Reference path escapes or aliases project: ' + str(path))
    if regular and not path.is_file():
        raise ValueError('Capture file missing: ' + str(path))
    return path


_PURE_SHA = ast.dump(ast.parse('''def sha(path):
    with pathlib.Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()
''').body[0], include_attributes=False)

def _safe_sha_leaf(tree):
    found = [x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == 'sha']
    if len(found) != 1 or ast.dump(found[0], include_attributes=False) != _PURE_SHA:
        return False
    # Only imports, inert function definitions, docstrings and the simple error
    # class initialize this exact module. Any new executable initialization,
    # decorators/default calls or aliasing falls back to the full import scan.
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if any(alias.asname == 'sha' or (alias.asname is None and alias.name == 'sha')
                   for alias in node.names):
                return False
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defaults = list(node.args.defaults) + [x for x in node.args.kw_defaults if x]
            arguments = node.args.posonlyargs + node.args.args + node.args.kwonlyargs
            arguments += [x for x in (node.args.vararg, node.args.kwarg) if x]
            if (node.decorator_list or node.returns or any(x.annotation for x in arguments)
                    or any(not isinstance(x, ast.Constant) for x in defaults)):
                return False
        elif isinstance(node, ast.ClassDef):
            if node.name != 'ContextError' or node.keywords or node.decorator_list or len(node.bases) != 1 or not isinstance(node.bases[0], ast.Name) or node.bases[0].id != 'ValueError':
                return False
            if any(not isinstance(x, ast.Pass) and not (isinstance(x, ast.Expr) and isinstance(x.value, ast.Constant) and isinstance(x.value.value, str)) for x in node.body):
                return False
        elif not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)):
            return False
    return True

def _initialization_imports(tree):
    # Safe-leaf recognition permits no executing nested bodies other than the
    # inert error class. Only actual top-level imports execute at module load.
    return [x for x in tree.body if isinstance(x, (ast.Import, ast.ImportFrom))]

def _closure(root):
    pending = [(name, False) for name in EXTRACTORS]
    result, visited = {}, {}
    while pending:
        name, sha_only = pending.pop()
        if name in visited and (visited[name] is False or sha_only is True):
            continue
        relative = 'dependency-graph/' + name + '.py'
        path = _inside(root, relative, regular=True)
        result[relative] = _sha(path)  # ALWAYS the whole original module hash.
        tree = ast.parse(path.read_text(), filename=relative)
        limited = name == 'context_runtime' and sha_only and _safe_sha_leaf(tree)
        visited[name] = bool(limited)
        if limited:
            nodes = _initialization_imports(tree)
        else:
            nodes = list(ast.walk(tree))
            # A changed sha with dynamic imports has no statically provable
            # dependency closure: refuse instead of silently ignoring a callee.
            if name == 'context_runtime' and any(isinstance(x, ast.Call) and
                    ((isinstance(x.func, ast.Name) and x.func.id == '__import__') or
                     (isinstance(x.func, ast.Attribute) and x.func.attr == 'import_module')) for x in nodes):
                raise ValueError('Dynamic context_runtime import requires explicit extraction dependency review')
        for node in nodes:
            imports = ([node.module.split('.')[0]] if isinstance(node, ast.ImportFrom) and node.module
                       else [alias.name.split('.')[0] for alias in node.names]
                       if isinstance(node, ast.Import) else [])
            for module in imports:
                if (root / 'dependency-graph' / (module + '.py')).is_file():
                    leaf = (module == 'context_runtime' and isinstance(node, ast.ImportFrom)
                            and len(node.names) == 1 and node.names[0].name == 'sha')
                    pending.append((module, leaf))
    return dict(sorted(result.items()))


def _metadata(root, source, bindings):
    result, refs = {}, {}
    for name in METADATA:
        path = _inside(root, source / name, regular=True)
        digest = _sha(path)
        if bindings['source_metadata'].get(name) != digest:
            raise ValueError('Original capture metadata binding mismatch: ' + name)
        result[name] = json.loads(path.read_text())
        refs[name] = {'path': str(path), 'sha256': digest}
    return result, refs


def _owner(owner):
    if not isinstance(owner, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]*', owner):
        raise ValueError('Unsafe owner identity')
    return owner.replace(':', '-')


def _capture(root, source, owner, row, plan):
    directory = _inside(root, source / 'observations' / _owner(owner))
    ast_path = _inside(root, directory / 'ast.json', regular=True)
    gcc_path = _inside(root, directory / '0000.json', regular=True)
    hashes = {'ast_sha256': _sha(ast_path), 'gcc_sha256': _sha(gcc_path)}
    captured, gcc = json.loads(ast_path.read_text()), json.loads(gcc_path.read_text())
    if captured.get('passed') is not True or captured.get('identity_version') != VERSION:
        raise ValueError('AST did not pass with the current identity contract')
    if plan.get('identity_version') != VERSION:
        raise ValueError('Original plan identity contract differs')
    inputs = captured.get('input_sha256')
    if not isinstance(inputs, dict) or not inputs:
        raise ValueError('Captured input hashes absent')
    source_file = Path(row['file'])
    if not source_file.is_absolute() or not source_file.resolve().is_relative_to(root):
        raise ValueError('Compile source is not a current project file')
    source_key = str(source_file.resolve())
    if source_key not in inputs:
        raise ValueError('Source omitted from AST input hashes')
    for value, digest in inputs.items():
        path = Path(value)
        if not path.is_absolute() or not path.resolve().is_relative_to(root) or not path.is_file():
            raise ValueError('Captured project input missing/outside project: ' + value)
        if _sha(path) != digest:
            raise ValueError('Captured source/include changed: ' + value)
    if captured.get('source') not in (str(source_file), str(source_file.relative_to(root))):
        raise ValueError('AST source identity differs')
    units = [n for n in captured.get('nodes', {}).values() if n.get('kind') == 'TranslationUnit']
    if len(units) != 1 or units[0].get('metadata', {}).get('compile_command') != context_descriptor(root, row):
        raise ValueError('AST compile-command context differs')
    if type(gcc.get('returncode')) is not int or gcc['returncode'] != 0 or not gcc.get('symbols'):
        raise ValueError('GCC capture failed or lacks parsed symbols')
    if gcc.get('source') != row['file'] or gcc.get('source_sha256') != inputs[source_key]:
        raise ValueError('GCC source identity/hash differs')
    scratch = _inside(root, gcc['scratch'])
    if not scratch.is_relative_to(directory):
        raise ValueError('GCC scratch is outside the exact owner capture')
    dump = _inside(root, gcc['dump'], regular=True)
    if dump != scratch / 'unit.cgraph' or _sha(dump) != gcc.get('dump_sha256'):
        raise ValueError('GCC parsed dump binding differs')
    argv = list(row.get('arguments') or shlex.split(row['command']))
    argv[argv.index('-o') + 1] = str(scratch / 'unit.o')
    argv.append('-fdump-ipa-cgraph=' + str(dump))
    if gcc.get('argv') != argv:
        raise ValueError('GCC replay compile command differs')
    pair_bindings = []
    recovery = captured.get('recovery')
    if captured.get('parse_clean') is not True and not isinstance(recovery, dict):
        raise ValueError('Unclean AST has no bound GCC recovery')
    if recovery:
        if recovery.get('gcc_validation') != str(gcc_path) or recovery.get('sha256') != hashes['gcc_sha256']:
            raise ValueError('Captured AST/GCC recovery pair hash differs')
        pair_bindings.append({'kind': 'AST recovery GCC hash', 'sha256': recovery['sha256']})
    # Some captures carry explicit additional pair bindings; never invent them.
    for container, field, expected in ((captured, 'gcc_sha256', hashes['gcc_sha256']),
                                       (gcc, 'ast_sha256', hashes['ast_sha256'])):
        if field in container:
            if container[field] != expected:
                raise ValueError('Captured pair hash differs: ' + field)
            pair_bindings.append({'kind': field, 'sha256': expected})
    if _sha(ast_path) != hashes['ast_sha256'] or _sha(gcc_path) != hashes['gcc_sha256']:
        raise ValueError('Capture changed during verification')
    return directory, dict(hashes, ast_path=str(ast_path), gcc_path=str(gcc_path),
                           input_sha256=dict(inputs), captured_pair_bindings=pair_bindings,
                           historical_pair_seal_present=bool(pair_bindings))


def reuse_verified(root, source_output, destination_output, selected_rows, producer_bindings):
    """Return eligible/rejected per owner; only eligible owner-directory links are created.

    Invalid global metadata rejects all owners. Existing destinations are never
    adopted/overwritten. The caller decides extraction for rejects and still runs
    all normal source/publication/registration freshness gates afterwards.
    """
    root = Path(root).resolve()
    selected = list(selected_rows)
    receipt = {'version': 1, 'eligible': [], 'rejected': [], 'graph_freshness_claimed': False,
               'registration_performed': False,
               'scope': 'compiler observations only; staging/projection/registration remain required'}
    try:
        source = _inside(root, source_output)
        destination = _inside(root, destination_output)
        if source == root or destination == root or source.is_relative_to(destination) or destination.is_relative_to(source):
            raise ValueError('Capture and destination must be distinct independent project directories')
        if not source.is_dir():
            raise ValueError('Original compiler output absent')
        metadata, refs = _metadata(root, source, producer_bindings)
        plan, extracted = metadata['plan.json'], metadata['extract.json']
        if type(extracted.get('returncode')) is not int or extracted['returncode'] != 0:
            raise ValueError('Original extraction did not complete successfully')
        args = extracted.get('argv', [])
        tokens = []
        for value in args:
            tokens.extend(shlex.split(value))
        if len(tokens) < 2 or tokens[-2:] != [str(root / 'dependency-graph/refresh_extract.py'), str(source)]:
            raise ValueError('Successful extraction receipt targets a different output/producer')
        producers = _closure(root)
        for path, digest in producers.items():
            if producer_bindings['producers'].get(path) != digest or plan['producer_sha256'].get(path) != digest:
                raise ValueError('Compiler extraction producer changed/unbound: ' + path)
        previous = {}
        for owner, row in metadata['units.json']:
            _owner(owner)
            if owner in previous:
                raise ValueError('Duplicate owner in original units binding')
            previous[owner] = row
        names = [_owner(owner) for owner, _ in selected]
        if len(names) != len(set(names)):
            raise ValueError('Duplicate/colliding selected owner identities')
        receipt.update(source_metadata=refs, original_plan_producers=plan['producer_sha256'],
                       verified_extraction_producers=producers, original_extract=extracted)
    except (KeyError, ValueError, TypeError, OSError) as exc:
        receipt['rejected'] = [{'owner': owner, 'reason': str(exc)} for owner, _ in selected]
        return receipt
    for owner, row in selected:
        target = destination / 'observations' / _owner(owner)
        try:
            if previous.get(owner) != row:
                raise ValueError('Selected owner/compile command differs from original bound units')
            directory, binding = _capture(root, source, owner, row, plan)
            if target.exists() or target.is_symlink():
                raise ValueError('Destination owner already exists; never overwrite/adopt')
            # Recheck immutable metadata and producer closure immediately before reference creation.
            for name, ref in refs.items():
                if _sha(_inside(root, source / name, regular=True)) != ref['sha256']:
                    raise ValueError('Original capture metadata changed during verification')
            if any(_sha(_inside(root, path, regular=True)) != digest for path, digest in producers.items()):
                raise ValueError('Extraction producers changed during reuse verification')
            _inside(root, target.parent)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.symlink_to(directory, target_is_directory=True)
            receipt['eligible'].append(dict(owner=owner, destination_link=str(target),
                                            source_directory=str(directory), **binding))
        except (KeyError, ValueError, TypeError, OSError) as exc:
            receipt['rejected'].append({'owner': owner, 'reason': str(exc)})
    return receipt
