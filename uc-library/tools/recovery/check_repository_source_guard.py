"""Exercise current, stale and escaped upstream dependency records read-only."""
import hashlib
import importlib.util
import json
from pathlib import Path

repo=Path('/home/rs/projects/opencs/ai-line-analysis')
lib=repo/'uc-library'
spec=importlib.util.spec_from_file_location('readiness',lib/'tools/merge_readiness.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
name='third_party/ccl-framework/core/public/corevector.h'
digest=hashlib.sha256((repo/name).read_bytes()).hexdigest()
cases=[('current_source',{'repository_sources':{name:digest}},True),
       ('stale_source',{'repository_sources':{name:'0'*64}},False),
       ('absolute_path',{'repository_sources':{str(repo/name):digest}},False),
       ('escaped_path',{'repository_sources':{'third_party/ccl-framework/core/../../../AGENTS.md':digest}},False),
       ('legacy_without_extra_dependencies',{},True),
       ('malformed_dependency_set',{'repository_sources':None},False)]
for label,entry,expected in cases:
    assert module.repository_sources_match(lib,entry)==expected,label
report=dict(passed=True,cases=[row[0] for row in cases],
            validator_sha256=hashlib.sha256((lib/'tools/merge_readiness.py').read_bytes()).hexdigest(),
            source=name,source_sha256=digest,scope='Metadata dependency admission only; vendor files unchanged')
out=repo/'evidence/recovery/2026-10-27/repository-source-guard/validation.json'
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
