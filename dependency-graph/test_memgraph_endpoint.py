import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch
from context_runtime import ContextError
from memgraph_endpoint import memgraph_uri

class EndpointTests(unittest.TestCase):
    def setUp(self):
        base=pathlib.Path(__file__).resolve().parents[1]/'temp/test-work/memgraph-endpoint';base.mkdir(parents=True,exist_ok=True)
        self.root=pathlib.Path(tempfile.mkdtemp(dir=base));self.config=self.root/'dependency-graph/state/memgraph-endpoint.json';self.config.parent.mkdir(parents=True)
    def test_default_for_preserved_dev_setup(self):
        with patch.dict('os.environ',{},clear=True):self.assertEqual(memgraph_uri(self.root),'bolt://dependency-graph-memgraph:7687')
    def test_verified_remote_endpoint(self):
        self.config.write_text(json.dumps({'status':'ready','uri':'bolt://192.168.50.190:7687'}))
        with patch.dict('os.environ',{},clear=True):self.assertEqual(memgraph_uri(self.root),'bolt://192.168.50.190:7687')
    def test_pending_blocks_even_override(self):
        self.config.write_text(json.dumps({'status':'migration_pending'}))
        with patch.dict('os.environ',{'MEMGRAPH_URI':'bolt://localhost:7687'},clear=True):
            with self.assertRaisesRegex(ContextError,'migration pending'):memgraph_uri(self.root)
    def test_credentials_and_invalid_uris_rejected(self):
        for uri in ('https://host','bolt://name:secret@host','bolt://host/path','bolt://host:99999','bolt://host?query=x'):
            with patch.dict('os.environ',{'MEMGRAPH_URI':uri},clear=True):
                with self.assertRaises(ContextError):memgraph_uri(self.root)
