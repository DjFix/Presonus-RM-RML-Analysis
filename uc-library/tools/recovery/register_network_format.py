"""Register frozen network candidate paths without changing C++ bytes."""
import hashlib,json,subprocess,sys
from pathlib import Path
assert sys.platform.startswith('linux')
lib=Path('uc-library');p=lib/'candidates/uc-network-manager-services/validation/archive-closure-01/format-paths.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(p)=='6e1f1ab36661ee8af636a3ac30f94ada600e2e932d40eb7182d41db36105efd1'
paths=json.loads(p.read_text());assert len(paths)==34 and all(isinstance(n,str) for n in paths)
assert all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in paths)
before={n:sha(lib/n) for n in paths}
out=Path('evidence/recovery/2026-10-27/network-format-registration-01');out.mkdir(exist_ok=False)
index=lib/'validation/formatting.json';(out/'formatting.before.json').write_bytes(index.read_bytes())
cmd=[sys.executable,str(lib/'tools/format_cpp.py'),'--library',str(lib),'--formatter',str(lib/'.venv/bin/clang-format'),'--config','.clang-format','--path-list',str(p)]
r=subprocess.run(cmd,capture_output=True,text=True)
(out/'format.log').write_text(r.stdout+r.stderr)
assert r.returncode==0,r.stdout+r.stderr
assert before=={n:sha(lib/n) for n in paths}
(out/'validation.json').write_text(json.dumps(dict(passed=True,files=before,source_unchanged=True,formatting_sha256=sha(index),path_list_sha256=sha(p)),indent=2)+'\n')
print(r.stdout)
