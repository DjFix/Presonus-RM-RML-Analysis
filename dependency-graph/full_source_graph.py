"""Source AST graph for every compile command; unresolved dispatch stays explicit."""
import argparse
import ctypes
import concurrent.futures
import functools
import hashlib
import json
import os
import pathlib
import shlex
import sqlite3
import sys
import time

from code_identity import CursorCache, context_id, indirect_id

ROOT = pathlib.Path(os.environ.get('DEPENDENCY_GRAPH_ROOT', pathlib.Path(__file__).resolve().parents[1]))
FUNCTIONS = {'FUNCTION_DECL', 'CXX_METHOD', 'CONSTRUCTOR', 'DESTRUCTOR',
             'CONVERSION_FUNCTION', 'FUNCTION_TEMPLATE'}
TYPES = {'CLASS_DECL', 'STRUCT_DECL', 'CLASS_TEMPLATE', 'ENUM_DECL',
         'UNION_DECL', 'TYPEDEF_DECL', 'TYPE_ALIAS_DECL'}


def sha(path):
    return hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()


@functools.lru_cache(maxsize=None)
def normalized(path):
    p = pathlib.Path(path).resolve()
    return str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)


def label_path(path):
    return normalized(str(path))


def arguments(row):
    argv = row.get('arguments') or shlex.split(row['command'])
    result = []
    skip = False
    for value in argv[1:]:
        if skip:
            skip = False
            continue
        if value in ('-o', '-MF', '-MT', '-MQ'):
            skip = True
        elif value not in ('-c', '-MD', '-MMD', row['file']):
            result.append(value)
    return result


def extract(row, output):
    from clang import cindex as ci
    os.chdir(row['directory'])
    start = time.perf_counter()
    args = arguments(row) + row.get('analysis_args', [])
    argv = row.get('arguments') or shlex.split(row['command'])
    object_path = pathlib.Path(row['directory']) / argv[argv.index('-o') + 1]
    depfile = pathlib.Path(str(object_path) + '.d')
    before = {str(pathlib.Path(row['file'])): sha(pathlib.Path(row['file']))}
    if depfile.exists():
        for p in shlex.split(depfile.read_text().replace('\\\n', '').partition(': ')[2]):
            p = pathlib.Path(row['directory']) / p
            if p.is_relative_to(ROOT) and p.is_file():
                before[str(p)] = sha(p)
    tu = ci.Index.create().parse(row['file'], args=args)
    diagnostics = [{'severity': d.severity, 'text': str(d)} for d in tu.diagnostics]
    errors = [d for d in diagnostics if d['severity'] >= ci.Diagnostic.Error]
    recovery = None
    if errors and row.get('gcc_validation'):
        gcc_path = pathlib.Path(row['gcc_validation'])
        gcc = json.loads(gcc_path.read_text())
        allowed = ('/Presonus/Panel/alert_manager.cpp', '/Presonus/NOAA/TCardSPIService.cpp')
        source_scope = (row['file'].endswith(allowed) or
                        row['file'].startswith(str(ROOT / 'third_party/ccl-framework') + '/'))
        known = (source_scope and errors and all(
            "explicit specialization of 'theInstance' after instantiation" in e['text'] for e in errors))
        if known and gcc['returncode'] == 0 and gcc['source_sha256'] == before[row['file']]:
            recovery = {'kind': 'Clang recovery AST for GCC-valid singleton specialization',
                        'gcc_validation': str(gcc_path), 'sha256': sha(gcc_path)}
    if errors and recovery is None:
        output.write_text(json.dumps({'source': row['file'], 'passed': False,
                                       'diagnostics': diagnostics, 'args': args}, indent=2) + '\n')
        return False
    nodes = {}
    edges = set()
    unknown = []
    includes = {}
    main = label_path(row['file'])
    unit = 'tu:' + context_id(ROOT, row)
    nodes[unit] = {'kind': 'TranslationUnit', 'label': main,
                   'metadata': {'source': main, 'compile_command': row,
                                'parse_clean': not errors, 'recovery': recovery}}
    locations = {}
    cache = CursorCache()
    bodies = {}
    visited_bodies = set()

    def location(cur):
        loc = cur.location
        path = label_path(loc.file) if loc.file else None
        return {'path': path, 'line': loc.line, 'column': loc.column}

    def own(cur):
        f = cur.location.file
        return bool(f and str(f).startswith(str(ROOT) + '/'))

    def entity(cur):
        cached = cache.get(cur)
        if cached is not None:
            return cached
        kind = cur.kind.name
        if kind in FUNCTIONS:
            category = 'Function'
        elif kind in TYPES:
            category = 'Type'
        else:
            category = 'Data'
        loc = location(cur)
        mangled = cur.mangled_name if category in ('Function', 'Data') else ''
        usr = cur.get_usr()
        internal = cur.linkage in (ci.LinkageKind.INTERNAL, ci.LinkageKind.NO_LINKAGE)
        definition = cur.get_definition() if category == 'Function' else None
        definition_loc = location(definition) if definition else None
        test_definition = bool(definition_loc and definition_loc['path'] and
                               definition_loc['path'].startswith('uc-library/tests/'))
        token = mangled or usr or f'{loc}:{cur.spelling}:{kind}'
        key = category.lower() + ':' + (main + ':' if internal or test_definition or mangled == 'main' else '') + token
        if key not in nodes:
            meta = dict(loc, mangled=mangled, usr=usr, cursor_kind=kind,
                        type=cur.type.spelling, linkage=cur.linkage.name,
                        source_definition=cur.is_definition(), source_port_declaration=True)
            if definition_loc:
                meta['definition_location'] = definition_loc
            nodes[key] = {'kind': category, 'label': cur.displayname or cur.spelling,
                          'metadata': meta}
            if loc['path']:
                filekey = 'file:' + loc['path']
                nodes[filekey] = {'kind': 'file', 'label': loc['path'], 'metadata': {}}
                edges.add((key, filekey, 'DECLARED_IN', json.dumps(loc, sort_keys=True)))
        elif cur.is_definition():
            nodes[key]['metadata']['source_definition'] = True
        cache.put(cur, key)
        if definition_loc and definition_loc['path']:
            filekey = 'file:' + definition_loc['path']
            nodes[filekey] = {'kind': 'file', 'label': definition_loc['path'], 'metadata': {}}
            edges.add((key, filekey, 'IMPLEMENTED_IN', json.dumps(definition_loc, sort_keys=True)))
        types = [cur.type]
        if category == 'Function':
            types = [cur.result_type] + [p.type for p in (cur.get_arguments() or [])]
            parent = cur.semantic_parent
            if parent and parent.kind.name in TYPES:
                edges.add((key, entity(parent), 'MEMBER_OF', main))
        for typ in types:
            for _ in range(4):
                if typ.kind in (ci.TypeKind.POINTER, ci.TypeKind.LVALUEREFERENCE, ci.TypeKind.RVALUEREFERENCE):
                    typ = typ.get_pointee()
                else:
                    break
            decl = typ.get_canonical().get_declaration()
            if decl and decl.kind.name in TYPES:
                target = entity(decl)
                if target != key:
                    edges.add((key, target, 'USES_TYPE' if category == 'Function' else 'HAS_TYPE', main))
        return key

    dynamic = ci.conf.lib.clang_Cursor_isDynamicCall
    dynamic.argtypes = [ci.Cursor]
    dynamic.restype = ctypes.c_uint
    overridden = ci.conf.lib.clang_getOverriddenCursors
    overridden.argtypes = [ci.Cursor, ctypes.POINTER(ctypes.POINTER(ci.Cursor)), ctypes.POINTER(ctypes.c_uint)]
    overridden.restype = None
    dispose = ci.conf.lib.clang_disposeOverriddenCursors
    dispose.argtypes = [ctypes.POINTER(ci.Cursor)]
    dispose.restype = None

    def visit(cur, function=None, parent_type=None):
        kind = cur.kind.name
        if cur.location.file and not own(cur):
            return
        if kind in TYPES:
            parent_type = entity(cur)
        if kind in FUNCTIONS:
            current = entity(cur)
            if kind == 'CXX_METHOD' and cur.is_virtual_method():
                array = ctypes.POINTER(ci.Cursor)()
                count = ctypes.c_uint()
                overridden(cur, ctypes.byref(array), ctypes.byref(count))
                for i in range(count.value):
                    base = array[i]
                    base._tu = tu
                    edges.add((current, entity(base), 'OVERRIDES', main))
                if array:
                    dispose(array)
            if parent_type:
                edges.add((parent_type, current, 'DECLARES_METHOD', main))
            if cur.is_definition():
                function = current
                edges.add((unit, current, 'DEFINES_FUNCTION', main))
            else:
                return
        if kind == 'LAMBDA_EXPR':
            candidates = [x for x in cur.type.get_declaration().get_children()
                          if x.kind.name == 'CXX_METHOD' and x.spelling == 'operator()']
            if candidates:
                target = entity(candidates[0])
            else:
                loc = location(cur)
                target = 'function:lambda:' + main + ':' + str(loc['line']) + ':' + str(loc['column'])
                nodes[target] = {'kind': 'Function', 'label': 'lambda body',
                                  'metadata': dict(loc, source_definition=True, lambda_identity_unresolved=True)}
                unknown.append({'function': target, 'kind': 'lambda_operator_identity', 'site': loc})
            if function:
                edges.add((function, target, 'CREATES_LAMBDA', main))
            function = target
        if kind == 'CXX_BASE_SPECIFIER' and parent_type and cur.referenced:
            edges.add((parent_type, entity(cur.referenced), 'INHERITS', main))
        if function:
            site = json.dumps(dict(location(cur), tu=unit), sort_keys=True)
            if kind == 'CALL_EXPR':
                ref = cur.referenced
                if ref and ref.kind.name in FUNCTIONS:
                    target = entity(ref)
                    relation = 'VIRTUAL_CALL' if dynamic(cur) else 'CALLS'
                    edges.add((function, target, relation, site))
                    definition = ref.get_definition()
                    if definition and own(definition) and target not in visited_bodies:
                        bodies[target] = definition
                    if relation == 'VIRTUAL_CALL':
                        unknown.append({'function': function, 'target': target,
                                        'kind': 'virtual_dispatch', 'site': json.loads(site)})
                else:
                    callkey = indirect_id(function, site)
                    nodes[callkey] = {'kind': 'UnresolvedCall', 'label': cur.spelling,
                                      'metadata': dict(location(cur), tu=unit)}
                    edges.add((function, callkey, 'INDIRECT_CALL', site))
                    unknown.append({'function': function, 'kind': 'indirect_call',
                                    'site': json.loads(site)})
            elif kind in ('DECL_REF_EXPR', 'MEMBER_REF_EXPR') and cur.referenced:
                ref = cur.referenced
                if ref.kind.name in FUNCTIONS:
                    edges.add((function, entity(ref), 'FUNCTION_REFERENCE', site))
                elif ref.kind.name in ('FIELD_DECL', 'VAR_DECL', 'ENUM_CONSTANT_DECL'):
                    edges.add((function, entity(ref), 'USES_DATA', site))
            elif kind in ('TYPE_REF', 'TEMPLATE_REF') and cur.referenced:
                edges.add((function, entity(cur.referenced), 'USES_TYPE', site))
        for child in cur.get_children():
            visit(child, function, parent_type)

    visit(tu.cursor)
    while bodies:
        target, definition = bodies.popitem()
        if target in visited_bodies:
            continue
        visited_bodies.add(target)
        for child in definition.get_children():
            visit(child, target)
    for inc in tu.get_includes():
        path = pathlib.Path(str(inc.include))
        if path.is_relative_to(ROOT) and path.is_file():
            includes[str(path)] = sha(path)
    includes[row['file']] = sha(pathlib.Path(row['file']))
    for p, digest in before.items():
        if sha(pathlib.Path(p)) != digest:
            raise ValueError('Source changed during analysis: ' + p)
    output.write_text(json.dumps({'passed': True, 'source': main,
                                   'parse_clean': not errors, 'recovery': recovery,
                                   'nodes': nodes, 'edges': sorted(edges),
                                   'unresolved': unknown, 'diagnostics': diagnostics,
                                   'input_sha256': includes,
                                   'ast_inputs_not_in_prior_gcc_depfile': sorted(set(includes) - set(before)),
                                   'seconds': time.perf_counter() - start}) + '\n')
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commands', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--index', type=int)
    parser.add_argument('--delayed-templates', action='store_true')
    parser.add_argument('--gcc-evidence-dir')
    args = parser.parse_args()
    rows = json.loads(pathlib.Path(args.commands).read_text())
    if args.gcc_evidence_dir:
        for index, row in enumerate(rows):
            row['gcc_validation'] = str(pathlib.Path(args.gcc_evidence_dir) / f'{index:04d}.json')
    output = pathlib.Path(args.out)
    if args.index is not None:
        assert not output.exists()
        if args.delayed_templates:
            rows[args.index]['analysis_args'] = ['-fdelayed-template-parsing']
        raise SystemExit(0 if extract(rows[args.index], output) else 2)
    output.mkdir(exist_ok=False)
    start = time.perf_counter()
    with concurrent.futures.ProcessPoolExecutor(max_workers=2) as pool:
        work = {pool.submit(extract, row, output / f'{index:04d}.json'): index
                for index, row in enumerate(rows)}
        completed = []
        for future in concurrent.futures.as_completed(work):
            index = work[future]
            try:
                passed = future.result()
                result = {'index': index, 'passed': passed}
            except Exception as exc:
                result = {'index': index, 'passed': False, 'exception': repr(exc)}
            completed.append(result)
            with (output / 'progress.jsonl').open('a') as stream:
                stream.write(json.dumps(result) + '\n')
    report = {'compile_commands': len(rows), 'passed': sum(x['passed'] for x in completed),
              'failures': [x for x in completed if not x['passed']],
              'seconds': time.perf_counter() - start, 'all_passed': all(x['passed'] for x in completed)}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
