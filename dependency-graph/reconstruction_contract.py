"""Evidence-bound work planning, separate from native context and complexity rank.

This checks a reviewed task contract, not the semantic truth of its evidence.
Root still reviews implementations and all ordinary packet/admission gates apply.
Unknown facts may be assigned bounded work; unavailable shared bases may not be
silently replaced with callbacks, fabricated layouts or production stubs.
"""
import hashlib
import json
import pathlib
import subprocess

SCOPES = ('declarations', 'state', 'lifecycle', 'providers')
STATUSES = {'established', 'bounded_work', 'not_required', 'missing'}


def identity(target):
    return (target['original_elf_sha256'], target['mangled'],
            target['address'], target['size'])


def evidence(root, refs):
    if not refs:
        raise ValueError('Nonempty hash-bound evidence required')
    for ref in refs:
        path = (root / ref['path']).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            raise ValueError('Evidence outside repository or absent')
        if hashlib.sha256(path.read_bytes()).hexdigest() != ref['sha256']:
            raise ValueError('Stale evidence: ' + ref['path'])
        kind = ref.get('kind')
        if kind not in {'cpp_declaration', 'cpp_implementation', 'provider_source', 'native_observation', 'review_record', 'compiled_symbol_audit'}:
            raise ValueError('Typed evidence kind required')
        if kind in {'cpp_declaration', 'cpp_implementation', 'provider_source'}:
            if pathlib.Path(ref['path']).suffix not in {'.cpp', '.hpp', '.h'}:
                raise ValueError('C++ source evidence must refer to actual source')
        if not ref.get('scope'):
            raise ValueError('Evidence scope required')


def evaluate(root, task, review, included_work=()):
    """Return planning disposition without claiming readiness or acquiring claims."""
    root = pathlib.Path(root)
    if review.get('version') != 1 or not review.get('reviewer'):
        raise ValueError('Versioned, attributed review required')
    if {identity(t) for t in review['targets']} != {identity(t) for t in task['targets']}:
        raise ValueError('Exact ELF/name/range identity mismatch')
    if len(review['targets']) != len(task['targets']):
        raise ValueError('Duplicate or expanded identities')
    owned = set(task['owned_files'])
    if set(review['owned_files']) != owned:
        raise ValueError('Reviewed ownership differs from task')
    if not review.get('domain'):
        raise ValueError('Explicit intended validation domain required')
    if review.get('existing_compiled_result'):
        existing = review['existing_compiled_result']
        evidence(root, existing['evidence'])
        if not any(ref['kind']=='compiled_symbol_audit' for ref in existing['evidence']):
            raise ValueError('Defined symbol audit required for existing-result routing')
        artifact = existing.get('artifact', {})
        evidence(root, [dict(artifact, kind='compiled_symbol_audit', scope='Actual compiled object/archive')])
        bindings = existing.get('source_bindings', [])
        evidence(root, bindings)
        if not any(ref['kind']=='cpp_implementation' for ref in bindings):
            raise ValueError('Existing object needs current source implementation binding')
        observed = subprocess.run(['/usr/bin/nm', '--defined-only', str(root / artifact['path'])],
                                  text=True, capture_output=True)
        if observed.returncode:
            raise ValueError('Compiled symbol inspection failed')
        names = {line.split()[-1] for line in observed.stdout.splitlines() if len(line.split()) >= 2}
        if not {t['mangled'] for t in task['targets']} <= names:
            raise ValueError('Existing result must cover exact actual defined symbols')
        return {'disposition': 'review_existing_result', 'dispatch_reconstruction': False,
                'reason': 'Compiled identity requires source/result audit; not ABI or behavior proof'}
    if set(review['requirements']) != set(SCOPES):
        raise ValueError('Every source-port requirement must be explicitly reviewed')
    missing, bounded = [], []
    for name, requirement in review['requirements'].items():
        status = requirement.get('status')
        if status not in STATUSES or not requirement.get('reason'):
            raise ValueError('Explicit status/reason required: ' + name)
        evidence(root, requirement.get('evidence', []))
        kinds = {ref['kind'] for ref in requirement['evidence']}
        if status == 'established':
            needed = {'declarations': {'cpp_declaration'}, 'state': {'cpp_declaration', 'cpp_implementation'},
                      'lifecycle': {'cpp_implementation', 'provider_source'},
                      'providers': {'cpp_implementation', 'provider_source'}}[name]
            if not kinds & needed:
                raise ValueError('Native context alone does not establish source contract: ' + name)
        if status == 'missing':
            missing.append(name)
        elif status == 'bounded_work':
            work = requirement.get('work', {})
            if (not work.get('objective') or not work.get('oracle_plan')
                    or not work.get('owned_files')
                    or not set(work['owned_files']) <= owned):
                raise ValueError('Unknown fact needs bounded owned work and oracle plan')
            bounded.append(name)
    included = set(included_work)
    for dependency in review.get('dependencies', []):
        evidence(root, dependency.get('evidence', []))
        kind = dependency.get('kind')
        if kind in ('pinned_provider', 'existing_implementation'):
            if not dependency.get('binding_domain'):
                raise ValueError('Actual provider/implementation binding scope required')
        elif kind == 'included_work':
            if (dependency.get('work_item_id') not in included
                    or not dependency.get('owned_files')
                    or not set(dependency['owned_files']) <= owned):
                missing.append('dependency:' + dependency.get('work_item_id', '?'))
        elif kind == 'unresolved':
            missing.append('dependency:' + dependency.get('name', '?'))
        else:
            raise ValueError('Unknown dependency kind')
    return {'disposition': 'prepare_dependencies_first' if missing else 'bounded_reconstruction',
            'dispatch_reconstruction': not missing, 'missing': missing,
            'bounded_work': bounded, 'domain': review['domain'],
            'readiness_or_abi_claim': False}


def validate_request(root, task):
    """New reconstruct requests must bind a reviewed source-port contract."""
    if task.get('mode') != 'reconstruct':
        return None
    binding = task.get('reconstruction_contract')
    if not binding:
        raise ValueError('Reconstruction requires reviewed declaration/state/lifecycle/provider contract')
    evidence(root, [dict(binding, kind='review_record', scope='Reviewed reconstruction plan, not readiness')])
    review = json.loads((pathlib.Path(root) / binding['path']).read_text())
    result = evaluate(root, task, review, task.get('included_dependency_work', []))
    if not result['dispatch_reconstruction']:
        raise ValueError('Reconstruction planning gate: ' + result['disposition'] + ' ' + str(result.get('missing', [])))
    return result


def bound_files(root, task):
    """Inputs to freeze along with a reviewed task; never mutable hard links."""
    binding = task.get('reconstruction_contract')
    if not binding:
        return []
    root = pathlib.Path(root)
    review = json.loads((root / binding['path']).read_text())
    paths = {binding['path']}
    def visit(value):
        if isinstance(value, dict):
            if {'path', 'sha256', 'scope', 'kind'} <= value.keys():
                evidence(root, [value])
                paths.add(value['path'])
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(review)
    return sorted(paths)
