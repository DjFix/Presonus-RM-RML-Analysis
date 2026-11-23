"""Audit reviewed handoff production flags against actual role OBJECT commands.

Accept an integration accepted-plan (reviewed canonical paths) or raw HANDOFFs.
This extends the control10x20 audit; it never configures/builds or edits inputs.
Optional baseline proves newly introduced out-of-scope flags only on comparable
production TUs. Missing baseline commands are reported, never called leak-free.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import shlex

ROLE = re.compile(r'CMakeFiles/presonus_(common|cs18|rm)_objects\.dir[/\\]')
SOURCE_FIELDS = ('required_production_source_compile_options',
                 'production_source_compile_options', 'source_compile_options')


def library_path(value):
    if not isinstance(value, str):
        raise ValueError('Production source must be a path string')
    path = Path(value.removeprefix('uc-library/'))
    if path.is_absolute() or '..' in path.parts or path.suffix != '.cpp' or not path.as_posix().startswith('src/'):
        raise ValueError(f'Invalid production translation unit: {value}')
    return 'uc-library/' + path.as_posix()


def handoff_task(handoff):
    build = handoff['build_integration']
    owned = [a['path'] for a in handoff['artifacts']
             if a.get('kind') == 'source' and a['path'].endswith('.cpp')]
    primary = build.get('primary_source')
    candidates = build.get('production_sources', build.get('new_production_sources', []))
    if isinstance(candidates, dict):
        candidates = list(candidates)  # Existing source -> role metadata.
    if not primary and len(candidates) == 1:
        primary = candidates[0]
    if not primary and len(owned) == 1:
        primary = owned[0]
    return {'task': handoff['task_id'], 'build': build,
            'plan': {'files': [{'path': p} for p in owned]},
            'canonical_registration': {'primary_source': primary}}


def collect_options(tasks):
    # Accepted integration plans may serialize coherent ownership across tasks;
    # use their complete reviewed ownership union, as the existing stager does.
    accepted = {library_path(r['path']) for t in tasks for r in t['plan']['files']
                if r['path'].endswith('.cpp') and r['path'].removeprefix('uc-library/').startswith('src/')}
    required = defaultdict(set)

    def add(source, options):
        source = library_path(source)
        if source not in accepted:
            raise ValueError(f'Compiler option names an unowned source: {source}')
        if not isinstance(options, list) or not all(
                isinstance(o, str) and o.startswith('-') and not any(c.isspace() for c in o)
                for o in options):
            raise ValueError(f'Invalid single-token compiler options for {source}: {options}')
        required[source].update(options)

    for task in tasks:
        build = task['build']
        production = build.get('production_compile_options', [])
        if isinstance(production, dict):
            for source, options in production.items():
                add(source, options)
        elif production:
            add(task['canonical_registration']['primary_source'], production)
        for field in SOURCE_FIELDS:
            for source, options in build.get(field, {}).items():
                add(source, options)
        for flag, sources in build.get('scoped_production_compile_options', {}).items():
            if not isinstance(flag, str) or not flag.startswith('-') or not isinstance(sources, list) or not sources:
                raise ValueError(f'Scoped option requires flag -> explicit owned files: {flag}')
            for source in sources:
                add(source, [flag])
        combined = build.get('compile_options')
        if isinstance(combined, dict):
            for source, options in combined.items():
                if source != 'test':
                    add(source, options)
    return dict(required)


def option_family(option):
    # Preserve ordered effective GCC/Clang switches for the forms used by the
    # handoffs. Unknown options use exact-token presence (explicitly reported).
    if re.fullmatch(r'-O(?:[0-3sgz]|fast)', option):
        return '-O'
    if option.startswith(('-f', '-m')):
        return option[:2] + option[2:].removeprefix('no-').split('=', 1)[0]
    return option


def effective(argv, wanted):
    family = option_family(wanted)
    return next((o for o in reversed(argv) if option_family(o) == family), None)


def production_commands(rows, repository):
    result = {}
    repository = Path(repository).resolve()
    for row in rows:
        argv = row.get('arguments') or shlex.split(row['command'])
        output = row.get('output', '')
        if not output and '-o' in argv:
            output = argv[argv.index('-o') + 1]
        match = ROLE.search(output)
        if not match:
            continue
        directory = Path(row['directory'])
        if not directory.is_absolute():
            directory = repository / directory
        path = (directory / row['file']).resolve()
        try:
            source = path.relative_to(repository).as_posix()
        except ValueError as exc:
            raise ValueError(f'Production source outside repository: {path}') from exc
        if source in result:
            raise ValueError(f'Production source compiled more than once: {source}')
        result[source] = {'argv': argv, 'output': output, 'role': match.group(1)}
    return result


def audit(tasks, rows, repository, baseline=None):
    required = collect_options(tasks)
    current = production_commands(rows, repository)
    failures = []
    for source, flags in required.items():
        if source not in current:
            failures.append(f'Missing production OBJECT command: {source}')
            continue
        if any(o.startswith('@') for o in current[source]['argv']):
            failures.append(f'Cannot prove effective options through response file: {source}')
        for flag in sorted(flags):
            actual = effective(current[source]['argv'], flag)
            if actual != flag:
                failures.append(f'{source}: required {flag}, effective {actual}')
    leak = {'baseline_available': baseline is not None,
            'comparable_production_sources': 0, 'sources_without_baseline': [],
            'sources_with_opaque_response_files': [],
            'new_out_of_scope_flags': [],
            'scope': 'Only requested flag families on comparable current/prior production TUs; no claim about unrelated flags or new TU defaults.'}
    if baseline is not None:
        previous = production_commands(baseline, repository)
        for source, row in current.items():
            if source not in previous:
                leak['sources_without_baseline'].append(source)
                continue
            if any(o.startswith('@') for o in row['argv'] + previous[source]['argv']):
                leak['sources_with_opaque_response_files'].append(source)
                continue
            leak['comparable_production_sources'] += 1
            for flag in set().union(*required.values()) if required else ():
                if flag not in required.get(source, ()) and effective(row['argv'], flag) == flag and effective(previous[source]['argv'], flag) != flag:
                    leak['new_out_of_scope_flags'].append({'source': source, 'flag': flag})
                    failures.append(f'New out-of-scope compiler flag: {source}: {flag}')
    return {'passed': not failures, 'errors': failures,
            'compiled_once_with_all_required_flags': {
                s: {'required': sorted(flags), 'output': current.get(s, {}).get('output'),
                    'role': current.get(s, {}).get('role')}
                for s, flags in sorted(required.items())},
            'scope_leak_audit': leak,
            'effective_option_policy': 'Ordered -f/-m positive/negative/value and -O families; other flags exact-token. Compiler response-file expansion and cross-family implications are not inferred.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', type=Path, default=Path.cwd())
    parser.add_argument('--accepted-plan', type=Path)
    parser.add_argument('--handoff', type=Path, action='append', default=[])
    parser.add_argument('--compile-commands', type=Path, required=True)
    parser.add_argument('--baseline-compile-commands', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if bool(args.accepted_plan) == bool(args.handoff):
        parser.error('Supply either --accepted-plan or one or more --handoff')
    bindings = {}

    def read(path):
        raw = path.read_bytes()
        bindings[str(path)] = hashlib.sha256(raw).hexdigest()
        return json.loads(raw)

    tasks = read(args.accepted_plan)['tasks'] if args.accepted_plan else [handoff_task(read(p)) for p in args.handoff]
    rows = read(args.compile_commands)
    baseline = read(args.baseline_compile_commands) if args.baseline_compile_commands else None
    report = audit(tasks, rows, args.repository, baseline)
    report['input_sha256'] = bindings
    report['producer'] = {'path': str(Path(__file__)),
                          'sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'passed': report['passed'], 'production_units_with_requirements': len(report['compiled_once_with_all_required_flags']), 'errors': report['errors']}))
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
