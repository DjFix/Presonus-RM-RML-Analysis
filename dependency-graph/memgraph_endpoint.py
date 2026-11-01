"""One explicit server address for source/native graph operators."""
import json
import os
from urllib.parse import urlsplit
from context_runtime import ContextError


def memgraph_uri(root):
    override=os.environ.get('MEMGRAPH_URI')
    path=root/'dependency-graph/state/memgraph-endpoint.json'
    config=json.loads(path.read_text()) if path.exists() else {}
    if config.get('status')=='migration_pending':
        raise ContextError('Memgraph migration pending; publication/selection must wait for verified PVE endpoint')
    uri=override or config.get('uri') or 'bolt://dependency-graph-memgraph:7687'
    parsed=urlsplit(uri)
    if parsed.scheme not in ('bolt','bolt+s') or not parsed.hostname or parsed.username or parsed.password or parsed.path not in ('','/') or parsed.query or parsed.fragment:
        raise ContextError('Invalid Memgraph server URI; no credentials/query/path permitted')
    try:
        if parsed.port is not None and not 1<=parsed.port<=65535:raise ValueError()
    except ValueError:raise ContextError('Invalid Memgraph port')
    return uri
