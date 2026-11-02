"""Resource planning tests; fixtures never modify host cgroups."""
import importlib.util
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('context_resources', ROOT / 'dependency-graph/context_resources.py')
resources = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resources)


class ResourcesTests(unittest.TestCase):
    def test_numeric_and_auto_stage_caps(self):
        detected = {'available_cpus': 16, 'available_memory_bytes': 32 * 1024**3, 'unknown': []}
        for jobs, expected in [('auto', 10), (1, 1), (4, 4), (8, 8)]:
            result = resources.choose_limits(jobs, 10, resources=detected)
            self.assertEqual(result['builder_jobs'], expected)
            self.assertEqual(result['selection_jobs'], min(expected, 4))
            self.assertEqual(result['slicing_jobs'], expected)
        limited = resources.choose_limits(8, 10, selection_jobs=2, slicing_jobs=3, resources=detected)
        self.assertEqual(limited['selection_jobs'], 2)
        self.assertEqual(limited['slicing_jobs'], 3)
        self.assertEqual(resources.choose_limits(8, 2, resources=detected)['builder_jobs'], 2)

    def test_memory_estimates_and_unknown(self):
        detected = {'available_cpus': 32, 'available_memory_bytes': 5 * 1024**3, 'unknown': []}
        self.assertEqual(resources.choose_limits('auto', 100, resources=detected)['builder_jobs'], 2)
        self.assertEqual(resources.choose_limits('auto', 100, slicing_memory_mib=512, resources=detected)['builder_jobs'], 8)
        detected['unknown'] = ['quota unavailable']
        self.assertEqual(resources.choose_limits(8, 100, resources=detected)['builder_jobs'], 1)
        self.assertEqual(resources.choose_limits('auto', 100, resources={})['builder_jobs'], 1)

    def test_invalid_values(self):
        for jobs in (0, -1, 'garbage', 1.5, True):
            with self.assertRaises(ValueError):
                resources.choose_limits(jobs, 10)
        for kwargs in ({'task_count': 0}, {'memgraph_cap': 0}, {'selection_jobs': 0}, {'slicing_memory_mib': -1}):
            args = {'task_count': 10, **kwargs}
            with self.assertRaises(ValueError):
                resources.choose_limits('auto', **args)

    def test_v2_parent_constraints_and_leaf_usage(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'temp') as name:
            base = pathlib.Path(name)
            proc, cg = base / 'proc', base / 'cgroup'
            (proc / 'self').mkdir(parents=True)
            leaf = cg / 'parent/leaf'
            leaf.mkdir(parents=True)
            (proc / 'self/cgroup').write_text('0::/parent/leaf\n')
            (proc / 'meminfo').write_text('MemAvailable: 16777216 kB\n')
            (leaf / 'cpu.max').write_text('max 100000')
            (cg / 'parent/cpu.max').write_text('250000 100000')
            (leaf / 'memory.max').write_text(str(8 * 1024**3))
            (leaf / 'memory.current').write_text(str(1024**3))
            (cg / 'parent/memory.max').write_text(str(6 * 1024**3))
            (cg / 'parent/memory.current').write_text(str(3 * 1024**3))
            result = resources.detect_resources(proc_root=proc, cgroup_root=cg, affinity=8)
            self.assertEqual(result['available_cpus'], 2)
            self.assertEqual(result['quota_cpus'], 2.5)
            self.assertEqual(result['available_memory_bytes'], 3 * 1024**3)
            self.assertFalse(result['unknown'])
            self.assertEqual(resources.choose_limits('auto', 10, resources=result)['builder_jobs'], 1)
            (leaf / 'memory.current').write_text('bad')
            result = resources.detect_resources(proc_root=proc, cgroup_root=cg, affinity=8)
            self.assertTrue(result['unknown'])

    def test_v1_constraints(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'temp') as name:
            base = pathlib.Path(name)
            proc, cg = base / 'proc', base / 'cgroup'
            (proc / 'self').mkdir(parents=True)
            (proc / 'self/cgroup').write_text('2:cpu,cpuacct:/leaf\n3:memory:/leaf\n')
            (proc / 'meminfo').write_text('MemAvailable: 16777216 kB\n')
            cpu, memory = cg / 'cpu,cpuacct/leaf', cg / 'memory/leaf'
            cpu.mkdir(parents=True)
            memory.mkdir(parents=True)
            (cpu / 'cpu.cfs_quota_us').write_text('400000')
            (cpu / 'cpu.cfs_period_us').write_text('100000')
            (memory / 'memory.limit_in_bytes').write_text(str(10 * 1024**3))
            (memory / 'memory.usage_in_bytes').write_text(str(1024**3))
            result = resources.detect_resources(proc_root=proc, cgroup_root=cg, affinity=2)
            self.assertEqual(result['available_cpus'], 2)
            self.assertEqual(result['available_memory_bytes'], 9 * 1024**3)
            self.assertFalse(result['unknown'])


if __name__ == '__main__':
    unittest.main()
