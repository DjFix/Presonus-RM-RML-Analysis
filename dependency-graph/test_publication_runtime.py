"""Publication-only fixes cannot relabel original fact execution on resume."""
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch
import refresh_publish as rp
from context_runtime import ContextError, sha


class RuntimeTests(unittest.TestCase):
    def fixture(self, directory, change):
        root = pathlib.Path(directory)
        base = root / 'dependency-graph'
        base.mkdir()
        out = root / 'pending'
        out.mkdir()
        names = ['batch_publication.py', 'refresh_publish.py', 'refresh_facts.py', 'memgraph_endpoint.py']
        original, archives = {}, {}
        for name in names:
            p = base / name
            p.write_text('original\n')
            rel = str(p.relative_to(root))
            original[rel] = sha(p)
            a = out / name
            a.write_bytes(p.read_bytes())
            archives[rel] = dict(path=name, sha256=sha(a))
        plan = dict(producer_sha256=original)
        (out / 'plan.json').write_text(json.dumps(plan))
        (out / 'delta.sqlite').write_bytes(b'immutable delta')
        (out / 'refresh-report.json').write_text('{"stage": "original"}')
        (out / 'stage-report.json').write_bytes((out / 'refresh-report.json').read_bytes())
        (base / change).write_text('reviewed fix\n')
        manifest = dict(version=1, scope='publication_runtime_only', approved=True,
                        reason='Reviewed request planner fix', stage_plan_sha256=sha(out / 'plan.json'),
                        delta_sha256=sha(out / 'delta.sqlite'), stage_producer_sha256=original,
                        publication_producer_sha256={p:sha(root/p) for p in original},
                        stage_producers=archives,
                        stage_report=dict(path='stage-report.json', sha256=sha(out/'stage-report.json')))
        (out/'publication-runtime.json').write_text(json.dumps(manifest))
        return root, base, out, plan

    def test_publication_fix_bound_once_without_rewriting_stage(self):
        scratch = pathlib.Path(__file__).resolve().parents[1]/'temp/test-work'
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as d:
            root, base, out, plan = self.fixture(d, 'batch_publication.py')
            original_plan = (out/'plan.json').read_bytes()
            with patch.object(rp, 'ROOT', root), patch.object(rp, 'BASE', base):
                first = rp.publication_runtime(out, plan, True)
                self.assertEqual(first, rp.publication_runtime(out, plan, True))
                self.assertEqual(original_plan, (out/'plan.json').read_bytes())
                (out/'delta.sqlite').write_bytes(b'changed')
                with self.assertRaisesRegex(ContextError, 'staged delta changed'):
                    rp.publication_runtime(out, plan, True)

    def test_fact_producer_change_cannot_be_publication_supersession(self):
        scratch = pathlib.Path(__file__).resolve().parents[1]/'temp/test-work'
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as d:
            root, base, out, plan = self.fixture(d, 'refresh_facts.py')
            with patch.object(rp, 'ROOT', root), patch.object(rp, 'BASE', base):
                with self.assertRaisesRegex(ContextError, 'compiler or fact producers'):
                    rp.publication_runtime(out, plan, True)
            self.assertFalse((out/'publication-runtime.accepted.json').exists())

if __name__ == '__main__':
    unittest.main()
