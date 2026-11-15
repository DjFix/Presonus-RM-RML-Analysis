"""Read-only replay of staging computations on a fixed real compiler capture.

Never publishes, mutates operational SQLite, or copies databases. Before/after
runs bind identical workload inputs and compare exact semantic output digests.
Use the publisher container for the same Python dependencies and CPU limit.
"""
import argparse
import ast
import cProfile
import hashlib
import json
from pathlib import Path
import pstats
import sqlite3
import time

from unchanged_observations import ObservationEquivalence
from refresh_facts import facts
from refresh_publish import build_facts

ROOT = Path(__file__).resolve().parents[1]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--reference-source', help='Project-local archived producer supplying the original build_facts function')
    parser.add_argument('--compare', help='Require identical workload and phase outputs to a prior RESULT.json')
    parser.add_argument('--normalizer', choices=('reference','optimized'), default='optimized')
    parser.add_argument('--profile', action='store_true', help='Include cProfile overhead in both compared runs')
    parser.add_argument('--phases', default='capture_equivalence,generate_changed_facts,build_facts,input_hash_checks,candidate_seal')
    args = parser.parse_args()
    import code_identity, stage_normalization, refresh_facts, unchanged_observations
    normalizer = code_identity.normalize_ast if args.normalizer == 'reference' else stage_normalization.normalize_ast
    refresh_facts.normalize_ast = unchanged_observations.normalize_ast = normalizer
    build_function = build_facts
    reference_build_hash = None
    if args.reference_source:
        # Execute only this explicitly selected trusted repository function;
        # do not import a second checkout or run historical module initializers.
        reference_path = (ROOT/args.reference_source).resolve()
        if not reference_path.is_relative_to(ROOT): raise ValueError('Reference source must remain project-local')
        source = reference_path.read_text()
        tree = ast.parse(source)
        definition = next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='build_facts')
        import refresh_publish
        namespace = dict(vars(refresh_publish))
        exec(compile(ast.Module(body=[definition],type_ignores=[]),'reference-build-facts','exec'),namespace)
        build_function = namespace['build_facts']
        reference_build_hash = hashlib.sha256(source.encode()).hexdigest()
    selected_phases = set(args.phases.split(','))
    allowed = {'capture_equivalence','generate_changed_facts','build_facts','input_hash_checks','candidate_seal'}
    if not selected_phases or not selected_phases <= allowed:
        raise ValueError('Unknown measurement phase')
    capture = (ROOT / args.capture).resolve()
    output = (ROOT / args.out).resolve()
    if not capture.is_relative_to(ROOT) or not output.is_relative_to(ROOT / 'temp/recovery-work'):
        raise ValueError('Project-local capture and recovery output required')
    output.mkdir(parents=True, exist_ok=False)
    units = json.loads((capture / 'units.json').read_text())
    history = json.loads((capture / 'unchanged-observations.json').read_text())
    retained = {e['owner']: e for e in history['eligible']}
    connection = sqlite3.connect((ROOT / 'dependency-graph/state/refresh-index.sqlite').as_uri() + '?mode=ro', uri=True)
    connection.execute('PRAGMA query_only=ON')
    connection.execute('BEGIN')
    producer_paths = [Path(module.__file__).resolve() for module in (code_identity,stage_normalization,refresh_facts,unchanged_observations)] + [Path(__file__).resolve(), ROOT/'dependency-graph/refresh_publish.py']
    producer_hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in producer_paths}
    result = {'implementation_sha256': producer_hashes, 'phases': [], 'operational_writes': 0, 'graph_requests': 0,
              'scope': 'read-only computations; excludes SQLite mutations, commit and graph publication',
              'workload': digest([units, history]), 'profiled':args.profile, 'normalizer':args.normalizer, 'reference_build_sha256':reference_build_hash}
    profiler = cProfile.Profile()
    def phase(name, callback):
        if name not in selected_phases: return None
        start = time.perf_counter()
        if args.profile: profiler.enable()
        try:
            value = callback()
        finally:
            profiler.disable()
        entry = {'phase': name, 'seconds': time.perf_counter()-start, 'output_sha256': digest(value)}
        result['phases'].append(entry)
        (output/'progress.json').write_text(json.dumps(result,indent=2)+'\n')
        return value
    eq = ObservationEquivalence(ROOT)
    def compare():
        statuses = []
        for owner, row in units:
            if owner not in retained:
                continue
            entry = retained[owner]
            old = entry['retained']; ast = json.loads(Path(old['ast']).read_text())
            previous = dict(old, command=row, inputs=ast['input_sha256'], external_inputs=ast.get('external_inputs'))
            fresh = entry['fresh']
            statuses.append((owner, eq.check(owner,row,previous,fresh['ast'],fresh['gcc'])))
        eq.verify_retained()
        if not all(passed for _,passed in statuses):
            raise ValueError('Historical retained workload is no longer valid; inspect capture/input changes')
        return statuses
    phase('capture_equivalence',compare)
    catalog = connection.execute('SELECT value FROM meta WHERE key="catalog_snapshot"').fetchone()
    from refresh_publish import catalog_snapshot
    lookup = {}
    for row in catalog_snapshot(json.loads(catalog[0]))[2]:
        lookup.setdefault(row['mangled'],[]).append('catalog:'+row['anchor'])
    def generate():
        outputs=[]
        for owner,row in units:
            if owner in retained:
                continue
            directory=capture/'observations'/owner.replace(':','-')
            nodes,edges=facts(ROOT,owner,row,directory/'ast.json',directory/'0000.json',catalog_lookup=lookup)
            outputs.append((owner,digest([nodes,sorted(edges)]),len(nodes),len(edges)))
        return outputs
    phase('generate_changed_facts',generate)
    def build():
        nodes,edges,inputs=build_function(connection,capture)
        return [nodes,sorted(edges),inputs]
    phase('build_facts',build)
    def hash_inputs():
        from context_runtime import sha
        report = json.loads((capture/'refresh-report.json').read_text())
        checks=[(name,sha(name)==expected) for name,expected in sorted(report['input_sha256'].items())]
        if not all(passed for _,passed in checks): raise ValueError('Historical staging input changed')
        return checks
    phase('input_hash_checks',hash_inputs)
    def seal():
        from native_candidate_gate import seal_guard
        delta=sqlite3.connect((capture/'delta.sqlite').as_uri()+'?mode=ro',uri=True)
        try:
            value=seal_guard(ROOT,connection,delta)
            from native_candidate_ownership import unpack_guard
            expected=unpack_guard(json.loads((capture/'refresh-report.json').read_text())['native_candidate_guard'])
            if value != expected:
                raise ValueError('Current source/native state differs from historical sealed workload')
            return value
        finally: delta.close()
    phase('candidate_seal',seal)
    result['equivalence_counts']={key:len(eq.receipt[key]) for key in ('eligible','rejected')}
    connection.close()
    for path in producer_paths:
        if hashlib.sha256(path.read_bytes()).hexdigest() != producer_hashes[str(path.relative_to(ROOT))]:
            raise ValueError('Benchmark producer changed during execution: '+str(path))
    if args.compare:
        previous=json.loads((ROOT/args.compare).read_text())
        if result['workload'] != previous['workload']:
            raise ValueError('Comparison workload changed')
        old={phase['phase']:phase for phase in previous['phases']}
        comparisons=[]
        for entry in result['phases']:
            if entry['phase'] not in old or entry['output_sha256'] != old[entry['phase']]['output_sha256']:
                raise ValueError('Comparison output differs: '+entry['phase'])
            comparisons.append({'phase':entry['phase'],'before_seconds':old[entry['phase']]['seconds'],
                                'after_seconds':entry['seconds'],'identical_output':True})
        result['comparison']=comparisons
    if args.profile:
        profiler.dump_stats(str(output/'profile.pstats'))
        with (output/'profile.txt').open('w') as stream:
            pstats.Stats(profiler,stream=stream).sort_stats('cumulative').print_stats(50)
    (output/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
