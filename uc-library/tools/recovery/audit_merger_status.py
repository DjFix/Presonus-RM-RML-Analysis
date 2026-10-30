"""Exercise real readiness proof transitions in a project-temp snapshot only."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

repo = Path('/home/rs/projects/opencs/ai-line-analysis')
library = repo / 'uc-library'
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
stage = repo / 'temp/recovery-work/merger-status-audit' / stamp / 'library'
evidence = repo / 'evidence/recovery/2026-10-27/merger-status-audit' / stamp
stage.mkdir(parents=True)
evidence.mkdir(parents=True)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
ready = read(library / 'validation/ready-functions.json')['functions']
pending = read(library / 'validation/compiled-functions.json')['functions']
integration = read(library / 'validation/integration.json')
paths = {'validation/ready-functions.json', 'validation/compiled-functions.json',
         'validation/integration.json', 'validation/formatting.json'}
paths.update(integration['files'])
for row in ready + pending:
    paths.update(row['sources'])
    paths.add(row['validation'])
for role in ('client', 'server'):
    paths.update('recovered-all/' + role + '/' + name for name in ('manifest.json', 'symbols.json'))
for name in sorted(paths):
    source = (library / name).resolve(strict=True)
    assert source.is_relative_to(library)
    target = stage / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
original = next(row for row in ready if row['mangled'] == '_ZNK8Presonus4DICE11SysexPacket18getSysexCommandStrEh')
key = lambda row: (row['original_elf_sha256'], row['mangled'])
assert key(original) not in {key(row) for row in pending}
manifest = dict(demotions=[dict(original_elf_sha256=original['original_elf_sha256'],
    mangled=original['mangled'], previous_validation_sha256=original['validation_sha256'],
    reason='Staged audit: observed string pointer does not establish original static pointer return declaration.')])
test_pending = dict(original, portable_ready=False, cpp_compiled=True, mangling_namespace_checked=True)
fixtures = stage / 'validation/status-audit-inputs'
fixtures.mkdir()
(fixtures / 'pending.json').write_text(json.dumps(dict(functions=[test_pending])) + '\n')
(fixtures / 'ready.json').write_text(json.dumps(dict(functions=[original])) + '\n')
(fixtures / 'demote.json').write_text(json.dumps(manifest) + '\n')
bad = json.loads(json.dumps(manifest))
bad['demotions'][0]['previous_validation_sha256'] = '0' * 64
(fixtures / 'bad-demote.json').write_text(json.dumps(bad) + '\n')
prefix = 'validation/status-audit-inputs/'
tool = library / 'tools/merge_readiness.py'
commands = []
def snapshot():
    return {str(p.relative_to(stage)): sha(p) for p in stage.rglob('*') if p.is_file()}
def execute(name, args, success=True, readonly=False):
    before = snapshot()
    command = [sys.executable, str(tool), '--library', str(stage), *args]
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (evidence / (name + '.stdout.log')).write_text(result.stdout)
    (evidence / (name + '.stderr.log')).write_text(result.stderr)
    commands.append(dict(name=name, command=command, returncode=result.returncode))
    (evidence / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
    assert (result.returncode == 0) == success, (name, result.stderr)
    if readonly or not success:
        assert snapshot() == before, name + ': read-only/failure wrote files'
    return json.loads(result.stdout) if success else None
baseline = execute('baseline', ['--dry-run'], readonly=True)
assert baseline['portable_ready_entries'] == len(ready) and baseline['compiled_declaration_pending_entries'] == len(pending)
args = ['--pending', prefix + 'pending.json', '--demote', prefix + 'demote.json']
execute('bad-previous-proof', ['--pending', prefix + 'pending.json', '--demote', prefix + 'bad-demote.json'], success=False)
dry = execute('demotion-dryrun', [*args, '--dry-run'], readonly=True)
assert dry['portable_ready_entries'] == len(ready) - 1 and dry['compiled_declaration_pending_entries'] == len(pending) + 1
assert len(dry['demoted_entries']) == 1 and not dry['stale_previous_entries']
demoted = execute('demotion-apply', args)
new_ready = read(stage / 'validation/ready-functions.json')['functions']
new_pending = read(stage / 'validation/compiled-functions.json')['functions']
assert key(original) not in {key(row) for row in new_ready}
assert key(original) in {key(row) for row in new_pending}
assert not {key(row) for row in new_ready} & {key(row) for row in new_pending}
assert len(list((stage / 'validation/history').glob('classification-*.json'))) == 1
assert list((stage / 'validation/history').glob('compiled-functions-*.json'))
execute('reject-dual-input', ['--fragment', prefix + 'ready.json', '--pending', prefix + 'pending.json'], success=False)
promoted = execute('promotion-apply', ['--fragment', prefix + 'ready.json'])
assert promoted['portable_ready_entries'] == len(ready) and promoted['compiled_declaration_pending_entries'] == len(pending)
assert len(promoted['promoted_pending_entries']) == 1
assert len(list((stage / 'validation/history').glob('classification-*.json'))) == 2
report = dict(passed=True, scope='Actual proof/format/input snapshot; classification metadata tests only, no C++ build or original application execution',
    actual_project_ledgers_unchanged=True, stage=str(stage.relative_to(repo)),
    baseline_ready=len(ready), baseline_pending=len(pending), files_copied=len(paths),
    merger_sha256=sha(tool), baseline=baseline, demotion=demoted, promotion=promoted,
    cases=['baseline dryrun unchanged', 'wrong prior proof rejected unchanged',
           'demotion dryrun unchanged', 'explicit demotion with fresh pending',
           'dual ready/pending input rejected unchanged', 'validated promotion drops old pending'])
assert read(library / 'validation/ready-functions.json')['functions'] == ready
assert read(library / 'validation/compiled-functions.json')['functions'] == pending
(evidence / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(dict(passed=True, evidence=str(evidence.relative_to(repo)), copied=len(paths), cases=len(report['cases']))))
