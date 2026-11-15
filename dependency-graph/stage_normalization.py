"""Equivalent AST normalization for staging; extraction producer stays unchanged.

The original code_identity normalizer is retained as the extraction contract and
independent differential oracle. Staging avoids its duplicate full-tree copy and
memoizes identical provenance strings only while the identity map is unchanged.
"""
import copy
import functools
import json
from code_identity import VERSION, context_descriptor, digest, indirect_id


def normalize_ast(root, row, original):
    """Explicit legacy-to-v2 map; never rewrite a historical observation in place."""
    # Nodes, edges and unresolved entries are rebuilt below. Deep-copying them
    # first duplicates the full AST walk and allocation without adding isolation.
    ast = {key: copy.deepcopy(value) for key, value in original.items()
           if key not in ('nodes', 'edges', 'unresolved')}
    ast.update({key: original[key] for key in ('nodes', 'edges')})
    ast['unresolved'] = original.get('unresolved', [])
    tus = [key for key, node in ast['nodes'].items() if node['kind'] == 'TranslationUnit']
    if len(tus) != 1:
        raise ValueError('Expected exactly one translation unit')
    descriptor = context_descriptor(root, row)
    new_tu = 'tu:' + digest(descriptor)
    mapping = {tus[0]: new_tu}
    @functools.lru_cache(maxsize=4096)
    def rewrite_text(value):
        if value in mapping: return mapping[value]
        if value.startswith('{'):
            try: return json.dumps(rewrite(json.loads(value)), sort_keys=True)
            except (ValueError, TypeError): pass
        return value

    def rewrite(value):
        if isinstance(value, dict): return {k: rewrite(v) for k, v in value.items()}
        if isinstance(value, list): return [rewrite(v) for v in value]
        if isinstance(value, str): return rewrite_text(value)
        return copy.deepcopy(value)
    for src, dst, kind, evidence in ast['edges']:
        if kind == 'INDIRECT_CALL':
            target = indirect_id(mapping.get(src, src), rewrite(evidence))
            if dst in mapping and mapping[dst] != target:
                raise ValueError('Ambiguous indirect-call identity')
            mapping[dst] = target
            rewrite_text.cache_clear()  # The indirect identity map is still evolving.
    nodes = {}
    for key, node in ast['nodes'].items():
        node = rewrite(node)
        if node['kind'] == 'TranslationUnit':
            node['metadata']['compile_command'] = copy.deepcopy(descriptor)
        new_key = mapping.get(key, key)
        if new_key in nodes and nodes[new_key] != node:
            raise ValueError('Conflicting canonical nodes: ' + new_key)
        nodes[new_key] = node
    ast['nodes'] = nodes
    ast['edges'] = sorted(set(tuple(rewrite(v) for v in edge) for edge in ast['edges']))
    ast['unresolved'] = rewrite(ast.get('unresolved', []))
    ast['identity_version'] = VERSION
    return ast, mapping
