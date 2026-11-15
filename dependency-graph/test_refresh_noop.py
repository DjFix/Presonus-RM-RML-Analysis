import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch

import refresh_graph
from code_identity import VERSION
from context_runtime import ContextError, fingerprint, inventory, sha
from refresh_facts import connect


class RefreshNoopTests(unittest.TestCase):
    def test_current_generation_never_launches_extractor_or_publisher(self):
        scratch = pathlib.Path(__file__).resolve().parents[1] / 'temp/test-work'
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            root = pathlib.Path(directory)
            base = root / 'dependency-graph'
            (base / 'state').mkdir(parents=True)
            source = root / 'uc-library/src/example.cpp'
            source.parent.mkdir(parents=True)
            source.write_text('int example() { return 1; }\n')
            state = dict(files={'uc-library/src/example.cpp': dict(sha256=sha(source),
                          fingerprint=fingerprint(source))}, source_inventory=inventory(root),
                         automatic_refresh_version=1)
            path = base / 'state/current.json'
            path.write_text(json.dumps(state))
            active = dict(state=str(path.relative_to(root)), state_sha256=sha(path))
            (base / 'ACTIVE.json').write_text(json.dumps(active))
            c = connect(base / 'state/refresh-index.sqlite')
            c.execute('INSERT INTO meta VALUES(?,?)', ('identity_version', str(VERSION)))
            c.commit()
            c.close()
            with patch.object(refresh_graph, 'ROOT', root), patch.object(refresh_graph, 'BASE', base), \
                    patch.object(refresh_graph, 'docker') as docker, patch.object(refresh_graph, 'run') as run:
                self.assertEqual(refresh_graph.ensure_fresh(), {'refreshed': False})
                docker.assert_not_called()
                run.assert_not_called()
            self.assertFalse((root / 'temp/recovery-work/dependency-graph/refresh').exists())

    def test_full_refresh_requires_explicit_authorization(self):
        with patch.object(refresh_graph, 'check_existing_identity') as read:
            with self.assertRaisesRegex(ContextError, 'explicit --full-rebuild'):
                refresh_graph.ensure_fresh(force=True)
            with self.assertRaisesRegex(ContextError, 'explicit reason'):
                refresh_graph.ensure_fresh(full_rebuild=True)
            read.assert_not_called()


if __name__ == '__main__':
    unittest.main()
