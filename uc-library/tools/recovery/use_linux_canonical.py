"""Adopt already verified Linux evidence without repeating any build/test."""
import hashlib
import json
from pathlib import Path

repo=Path('/home/rs/projects/opencs/ai-line-analysis')
lib=repo/('uc-library' if (repo/'uc-library').is_dir() else 'uc-library')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=lib/'validation/integration-linux.json'
report=json.loads(source.read_text())
assert report['platform']=='linux' and report['ctest_passed']
for name,digest in report['files'].items():
    assert sha(lib/name)==digest,name
for name,digest in report['logs'].items():
    assert sha(repo/name)==digest,name
target=lib/'validation/integration.json'
previous=json.loads(target.read_text())
if target.read_bytes()!=source.read_bytes():
    history=lib/'validation/history'
    history.mkdir(exist_ok=True)
    backup=history/('integration-before-linux-canonical-'+sha(target)[:16]+'.json')
    if backup.exists(): assert backup.read_bytes()==target.read_bytes()
    else: backup.write_bytes(target.read_bytes())
    target.write_bytes(source.read_bytes())
print(json.dumps(dict(canonical_platform='linux',previous_platform=previous.get('platform'),test_suites=report['test_suites'],source_inputs=len(report['files']),new_builds_or_tests=0)))
