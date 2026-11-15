"""Bounded per-operation staging timings; no SQL hooks or payload retention."""
import json
import time


class StageTimings:
    def __init__(self):
        self.started = time.perf_counter()
        self.phases = {}

    def call(self, name, function, *args, **kwargs):
        start, cpu = time.perf_counter(), time.process_time()
        try:
            return function(*args, **kwargs)
        finally:
            phase = self.phases.setdefault(name, {'calls': 0, 'wall_seconds': 0, 'cpu_seconds': 0})
            phase['calls'] += 1
            phase['wall_seconds'] += time.perf_counter() - start
            phase['cpu_seconds'] += time.process_time() - cpu

    def save(self, path):
        elapsed = time.perf_counter() - self.started
        path.write_text(json.dumps({'version': 1, 'wall_seconds': elapsed,
            'phases': self.phases, 'other_seconds': elapsed - sum(p['wall_seconds'] for p in self.phases.values()),
            'scope': 'disjoint timed calls inside staging, including failed calls; excludes outer commit/publication'}, indent=2)+'\n')
