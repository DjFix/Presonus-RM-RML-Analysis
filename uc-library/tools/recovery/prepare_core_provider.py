"""Deploy the frozen provider02 packaging; keep the source candidate immutable."""
import hashlib
import json
from pathlib import Path
import shutil

repo = Path('/home/rs/projects/opencs/ai-line-analysis')
lib = repo / 'uc-library'
source = lib / 'validation/core-upstream/provider-integration-02'
proof = lib / 'validation/core-upstream/provider-integration-02-validation.json'
assert hashlib.sha256(proof.read_bytes()).hexdigest() == 'cf13e63b689bcf3ef1b8a63f6dfb5e2bbecd4fa3c41b45b7725c44b27e52b408'
target = lib / 'cmake/providerRoot'
assert not target.exists(), 'Refusing to replace an existing provider deployment'
names = ['CMakeLists.txt', 'cmake/presonus_ucConfig.cmake.in', 'tools/audit_install.py']
for name in ('cmake', 'native', 'provenance.json'):
    src = source / name
    dst = target / name
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst)
        names.extend(str(p.relative_to(lib)) for p in dst.rglob('*') if p.is_file())
    else:
        shutil.copy2(src, dst)
        names.append(str(dst.relative_to(lib)))
out = lib / 'validation/integration-core-provider-additions.json'
out.write_text(json.dumps(sorted(names), indent=2) + '\n')
print(json.dumps({'deployed_files': len(names), 'additional_list': str(out.relative_to(repo))}))
