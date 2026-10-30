"""Register three frozen constructor C++ paths without changing their bytes."""
import hashlib,json,subprocess,sys
from pathlib import Path
assert sys.platform.startswith('linux')
lib=Path('uc-library');p=lib/'candidates/dsp-biquad-calc/validation/constructor-format-paths.json'
paths=json.loads(p.read_text());assert len(paths)==3 and all(n.startswith('candidates/dsp-biquad-calc/') and '..' not in Path(n).parts for n in paths)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={n:sha(lib/n) for n in paths}
out=Path('evidence/recovery/2026-10-27/network-biquad-root/constructor-format-registration');out.mkdir(parents=True,exist_ok=False)
index=lib/'validation/formatting.json';(out/'formatting.before.json').write_bytes(index.read_bytes())
cmd=[sys.executable,str(lib/'tools/format_cpp.py'),'--library',str(lib),'--formatter',str(lib/'.venv/bin/clang-format'),'--config','.clang-format','--path-list',str(p)]
r=subprocess.run(cmd,capture_output=True,text=True);(out/'format.log').write_text(r.stdout+r.stderr)
assert r.returncode==0,r.stdout+r.stderr
assert before=={n:sha(lib/n) for n in paths}
(out/'validation.json').write_text(json.dumps(dict(passed=True,files=before,source_unchanged=True,formatting_sha256=sha(index)),indent=2)+'\n')
print(r.stdout)
