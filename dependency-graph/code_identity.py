"""Versioned source identities; capture paths and raw hashes are observations only."""
import copy
import hashlib
import json
import pathlib
import shlex

VERSION = 2


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def context_descriptor(root, row):
    root = pathlib.Path(root).resolve()
    directory = pathlib.Path(row['directory']).resolve()
    def path(value):
        p = pathlib.Path(value)
        p = (directory / p).resolve() if not p.is_absolute() else p.resolve()
        return str(p.relative_to(root)) if p.is_relative_to(root) else str(p)
    argv = list(row.get('arguments') or shlex.split(row['command']))
    normalized = []
    path_next = False
    # Preserve argument order, compiler, output target and every non-capture flag.
    # Do not discard macros/configuration simply because they contain paths.
    for token in argv:
        if path_next:
            normalized.append(path(token)); path_next = False
        elif token in ('-I', '-isystem', '-iquote', '-include', '-imacros', '-o', '-MF', '-MT', '-MQ'):
            normalized.append(token); path_next = True
        elif token.startswith('-I') and len(token) > 2:
            normalized.append('-I' + path(token[2:]))
        elif token.startswith(str(root) + '/'):
            normalized.append(path(token))
        else:
            normalized.append(token)
    return {'version': VERSION, 'directory': path(str(directory)), 'source': path(row['file']),
            'arguments': normalized, 'analysis_args': row.get('analysis_args', [])}


def context_id(root, row):
    return digest(context_descriptor(root, row))


def owner_id(root, group, row):
    return group + ':' + context_id(root, row)


def indirect_id(function, site):
    return 'unresolved:' + hashlib.sha256((function + site).encode()).hexdigest()


def normalize_ast(root, row, original):
    """Explicit legacy-to-v2 map; never rewrite a historical observation in place."""
    ast = copy.deepcopy(original)
    tus = [key for key, node in ast['nodes'].items() if node['kind'] == 'TranslationUnit']
    if len(tus) != 1:
        raise ValueError('Expected exactly one translation unit')
    new_tu = 'tu:' + context_id(root, row)
    mapping = {tus[0]: new_tu}
    def rewrite(value):
        if isinstance(value, dict): return {k: rewrite(v) for k, v in value.items()}
        if isinstance(value, list): return [rewrite(v) for v in value]
        if isinstance(value, str):
            if value in mapping: return mapping[value]
            if value.startswith('{'):
                try: return json.dumps(rewrite(json.loads(value)), sort_keys=True)
                except (ValueError, TypeError): pass
        return value
    for src, dst, kind, evidence in ast['edges']:
        if kind == 'INDIRECT_CALL':
            target = indirect_id(mapping.get(src, src), rewrite(evidence))
            if dst in mapping and mapping[dst] != target:
                raise ValueError('Ambiguous indirect-call identity')
            mapping[dst] = target
    nodes = {}
    for key, node in ast['nodes'].items():
        node = rewrite(node)
        if node['kind'] == 'TranslationUnit':
            node['metadata']['compile_command'] = context_descriptor(root, row)
        new_key = mapping.get(key, key)
        if new_key in nodes and nodes[new_key] != node:
            raise ValueError('Conflicting canonical nodes: ' + new_key)
        nodes[new_key] = node
    ast['nodes'] = nodes
    ast['edges'] = sorted(set(tuple(rewrite(v) for v in edge) for edge in ast['edges']))
    ast['unresolved'] = rewrite(ast.get('unresolved', []))
    ast['identity_version'] = VERSION
    return ast, mapping


class CursorCache:
    """Clang cursor hashes are bucket selectors, never equality proofs."""
    def __init__(self): self.buckets = {}
    def get(self, cursor):
        for previous, value in self.buckets.get(cursor.hash, []):
            if previous == cursor: return value
        return None
    def put(self, cursor, value):
        self.buckets.setdefault(cursor.hash, []).append((cursor, value))
