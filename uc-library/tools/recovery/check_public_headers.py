"""Compile all installed public headers together without changing the library."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--platform',choices=('mac','linux'),required=True)
p.add_argument('--install-tag',required=True)
p.add_argument('--phase',required=True)
p.add_argument('--upstream-core', action='store_true')
a=p.parse_args()
repo=Path('/home/rs/projects/opencs/ai-line-analysis')
prefix=repo/'temp/recovery-work'/('install-'+a.install_tag+'-'+a.platform)
directory=repo/'temp/recovery-work/public-header-composition'/a.phase/a.platform
evidence=repo/'evidence/recovery/2026-10-27/public-header-composition'/a.phase/a.platform
directory.mkdir(parents=True,exist_ok=True)
evidence.mkdir(parents=True,exist_ok=True)
headers=sorted((prefix/'include/presonus').rglob('*.hpp'))
assert headers,'no installed headers'
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
before={str(f.relative_to(prefix)):sha(f) for f in headers}
source=directory/'headers.cpp'
source.write_text(''.join('#include "'+str(f.relative_to(prefix/'include'))+'"\n' for f in headers)+'int main() { return 0; }\n')
command=['/usr/bin/c++','-std=c++17','-Wall','-Wextra','-Wpedantic','-I'+str(prefix/'include'),'-fsyntax-only',str(source)]
if a.upstream_core:
    assert a.platform == 'linux', 'upstream source provider is Linux-only'
    command[1:1] = ['-I'+str(prefix/'include/presonus-core-5'), '-pthread',
                    '-Ulinux', '-DNDEBUG=1', '-DCORE_USE_OPENSSL=1',
                    '-DPRESONUS_HAS_UPSTREAM_CORE=1']
result=subprocess.run(command,cwd=repo,env=dict(os.environ,TMPDIR=str(directory),TMP=str(directory),TEMP=str(directory)),text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(evidence/'compile.log').write_text(result.stdout)
assert before=={str(f.relative_to(prefix)):sha(f) for f in headers},'headers changed during check'
report=dict(platform=a.platform,command=command,returncode=result.returncode,header_hashes=before,translation_unit_sha256=sha(source),compile_log_sha256=sha(evidence/'compile.log'),scope='All installed public headers coexist in one C++17 translation unit; no link/runtime/ARM ABI claim')
(evidence/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(platform=a.platform,headers=len(headers),returncode=result.returncode)))
if result.returncode:
    print(result.stdout)
    raise SystemExit(result.returncode)
