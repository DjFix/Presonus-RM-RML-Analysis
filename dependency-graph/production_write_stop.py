"""Persistent stop of production derived-graph updates, not SQLite readiness.

There is deliberately no environment/CLI bypass. Reopening requires a separately
reviewed change after a new user instruction. Offline fixture roots and SQLite
files outside production graph storage can still exercise pure helpers.
"""
from pathlib import Path

PRODUCTION_ROOT = Path('/home/rs/projects/opencs/ai-line-analysis')
MESSAGE = ('Production graph updates are stopped by explicit user instruction. '
           'Preserve pending journals/captures; do not refresh, publish, resume, '
           'register, import or migrate the production graph. SQLite-only '
           'production issuance/admission and isolated offline tests remain available.')


class ProductionGraphUpdatesStopped(RuntimeError):
    pass


def require_graph_updates(root=None):
    root = Path(root).resolve() if root is not None else PRODUCTION_ROOT
    # Fail closed for the canonical checkout even if the policy file is removed.
    # A copied checkout carrying this policy is also not an isolated fixture.
    if root == PRODUCTION_ROOT.resolve() or (root / 'dependency-graph/PRODUCTION_GRAPH_STOP.json').exists():
        raise ProductionGraphUpdatesStopped(MESSAGE)


def require_graph_storage_write(path):
    path = Path(path).resolve()
    for base in (PRODUCTION_ROOT / 'dependency-graph/state',
                 PRODUCTION_ROOT / 'temp/recovery-work/dependency-graph/refresh'):
        if path.is_relative_to(base.resolve()):
            raise ProductionGraphUpdatesStopped(MESSAGE)
