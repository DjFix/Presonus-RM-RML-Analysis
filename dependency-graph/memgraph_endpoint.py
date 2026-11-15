"""One explicit server address for source/native graph operators."""
import json
import os
import re
from urllib.parse import urlsplit
from context_runtime import ContextError


DEFAULT_DOCKER_NETWORK = 'dependency-graph-experiment'


def endpoint_config(root):
    path = root/'dependency-graph/state/memgraph-endpoint.json'
    config = json.loads(path.read_text()) if path.exists() else {}
    if not isinstance(config, dict):
        raise ContextError('Invalid Memgraph endpoint configuration')
    if config.get('status') == 'migration_pending':
        raise ContextError('Memgraph migration pending; publication/selection must wait for verified PVE endpoint')
    return config


def validate_network(value):
    if (not isinstance(value, str) or value.lower() in ('host', 'none', 'bridge', 'default') or
            not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,62}', value)):
        raise ContextError('Invalid isolated Memgraph Docker network')
    return value


def memgraph_network(root):
    """One configured runner network; legacy configurations retain their route."""
    return validate_network(endpoint_config(root).get('docker_network', DEFAULT_DOCKER_NETWORK))


def memgraph_uri(root):
    override=os.environ.get('MEMGRAPH_URI')
    config=endpoint_config(root)
    uri=override or config.get('uri') or 'bolt://dependency-graph-memgraph:7687'
    parsed=urlsplit(uri)
    if parsed.scheme not in ('bolt','bolt+s') or not parsed.hostname or parsed.username or parsed.password or parsed.path not in ('','/') or parsed.query or parsed.fragment:
        raise ContextError('Invalid Memgraph server URI; no credentials/query/path permitted')
    try:
        if parsed.port is not None and not 1<=parsed.port<=65535:raise ValueError()
    except ValueError:raise ContextError('Invalid Memgraph port')
    return uri
