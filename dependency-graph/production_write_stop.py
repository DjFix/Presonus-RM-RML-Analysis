"""Reviewed production graph interlock; SQLite-only issuance is independent.

No environment/CLI override. A maintenance window requires a reviewed policy
and hash-bound accepted/committed package receipt. This does not launch work.
"""
import hashlib
import json
from pathlib import Path
import re

PRODUCTION_ROOT = Path('/home/rs/projects/opencs/ai-line-analysis')
MESSAGE = ('Production graph updates are stopped by explicit user instruction. '
           'Preserve pending journals/captures; do not refresh, publish, resume, '
           'register, import or migrate the production graph. SQLite-only '
           'production issuance/admission and isolated offline tests remain available.')
POLICY_PATH = 'dependency-graph/PRODUCTION_GRAPH_STOP.json'


class ProductionGraphUpdatesStopped(RuntimeError):
    pass


def _document(path):
    # Duplicate keys and oversized inputs must not silently select a permission.
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result
    data = path.read_bytes()
    if len(data) > 65536:
        raise ValueError('oversized policy/receipt')
    return data, json.loads(data, object_pairs_hook=unique_pairs)


def _maintenance_allowed(root):
    try:
        _, policy = _document(root / POLICY_PATH)
        if not isinstance(policy, dict):
            return False
        version = policy.get('version')
        if type(version) is not int:
            return False
        if policy.get('production_graph_updates') == 'stopped':
            # Existing stopped v1 stays valid; unknown versions never grant writes.
            return False
        if (version != 2 or set(policy) != {'version', 'production_graph_updates',
                                           'authority', 'boundary'}
                or policy['production_graph_updates'] != 'maintenance_update'
                or not isinstance(policy['authority'], str)
                or not policy['authority'].strip()):
            return False
        boundary = policy['boundary']
        if (not isinstance(boundary, dict)
                or set(boundary) != {'receipt', 'package_scope', 'commit'}
                or not isinstance(boundary['package_scope'], str)
                or not boundary['package_scope'].strip()
                or not isinstance(boundary['commit'], str)
                or re.fullmatch(r'[0-9a-f]{40}', boundary['commit']) is None):
            return False
        reference = boundary['receipt']
        if (not isinstance(reference, dict) or set(reference) != {'path', 'sha256'}
                or not isinstance(reference['path'], str)
                or not isinstance(reference['sha256'], str)
                or re.fullmatch(r'[0-9a-f]{64}', reference['sha256']) is None):
            return False
        relative = Path(reference['path'])
        receipt_path = (root / relative).resolve()
        if relative.is_absolute() or not receipt_path.is_relative_to(root):
            return False
        data, receipt = _document(receipt_path)
        if hashlib.sha256(data).hexdigest() != reference['sha256']:
            return False
        return (isinstance(receipt, dict)
                and set(receipt) == {'version', 'package_scope', 'commit',
                                     'accepted', 'committed'}
                and type(receipt['version']) is int and receipt['version'] == 1
                and receipt['accepted'] is True and receipt['committed'] is True
                and receipt['package_scope'] == boundary['package_scope']
                and receipt['commit'] == boundary['commit'])
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        return False


def require_graph_updates(root=None):
    root = Path(root).resolve() if root is not None else PRODUCTION_ROOT.resolve()
    # No-policy fixture roots stay usable. Canonical/mirrored policy roots fail
    # closed unless this exact reviewed maintenance receipt permits the window.
    if (root == PRODUCTION_ROOT.resolve() or (root / POLICY_PATH).exists()):
        if not _maintenance_allowed(root):
            raise ProductionGraphUpdatesStopped(MESSAGE)


def require_graph_storage_write(path):
    path = Path(path).resolve()
    for base in (PRODUCTION_ROOT / 'dependency-graph/state',
                 PRODUCTION_ROOT / 'temp/recovery-work/dependency-graph/refresh'):
        if path.is_relative_to(base.resolve()):
            require_graph_updates(PRODUCTION_ROOT)
