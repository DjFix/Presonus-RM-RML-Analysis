#!/usr/bin/env python3
"""Freeze source/API mapping and exact tool/input provenance under evidence."""
import argparse
import ctypes
import hashlib
import json
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from core_upstream_match import atomic, sha


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository',type=Path,required=True)
    parser.add_argument('--library',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True)
    args=parser.parse_args()
    repository=args.repository.resolve();library=args.library.resolve();evidence=args.evidence.resolve()
    assert not evidence.exists(),'Evidence snapshots are immutable; choose a new run name'
    mapping=library/'validation/core-upstream/source-map'
    summary=json.loads((mapping/'summary.json').read_text())
    config=json.loads((library/'validation/core-upstream/pass-2-bodies/configuration.json').read_text())
    source=Path(config['source']);commit=summary['commit']
    assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==commit
    assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain','--untracked-files=no'],text=True).strip()
    for name,digest in summary['inputs'].items():assert sha(library/name)==digest,name
    fragments=json.loads((mapping/'manual-recovery-exclusions.fragment.json').read_text())
    assert len(fragments['functions'])==sum(item['exact_encoded_interface_matches'] for item in summary['roles'].values())
    for item in fragments['functions']:
        assert item['skip_manual_reconstruction'] is True and item['original_function_verified'] is False and item['hardware_verified'] is False
        for candidate in item['upstream']:assert sha(source/candidate['path'])==candidate['source_sha256']
    tracked=json.loads((library/'validation/core-upstream/pass-2-bodies/source-files.json').read_text())
    for item in tracked['files']:
        path=source/item['path'];data=path.read_bytes()
        assert sha(path)==item['sha256']
        assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==item['git_blob_sha1']
    evidence.mkdir(parents=True)
    for directory in ('pass-1','pass-2-bodies','probes','source-map'):
        shutil.copytree(library/'validation/core-upstream'/directory,evidence/directory)
    tools=evidence/'tools';tools.mkdir()
    for tool in sorted((library/'tools').glob('core_upstream_*.py')):shutil.copy2(tool,tools/tool.name)
    shutil.copy2(library/'tools/extraction_verify_bounded.py',tools/'extraction_verify_bounded.py')
    for name in ('license.md','readme.md','.gitmodules'):
        shutil.copy2(source/name,evidence/('upstream-'+name.lstrip('.')))
    shutil.copy2(repository/'.gitmodules',evidence/'project.gitmodules')
    git=dict(commit=commit,
        history=subprocess.check_output(['git','-C',str(source),'log','--all','--reverse','--format=%H %cI %s'],text=True),
        refs=subprocess.check_output(['git','-C',str(source),'show-ref'],text=True),
        gitlink=subprocess.check_output(['git','-C',str(repository),'ls-files','--stage','--','third_party/ccl-framework'],text=True),
        staged_changes=subprocess.check_output(['git','-C',str(repository),'diff','--cached','--stat','--','.gitmodules','third_party/ccl-framework'],text=True))
    atomic(evidence/'git-provenance.json',git)
    class RawString(ctypes.Structure):_fields_=[('data',ctypes.c_void_p),('flags',ctypes.c_uint)]
    native=ctypes.CDLL(config['libclang']);version=native.clang_getClangVersion;version.restype=RawString
    string=native.clang_getCString;string.argtypes=[RawString];string.restype=ctypes.c_char_p
    dispose=native.clang_disposeString;dispose.argtypes=[RawString]
    result=version();clang_version=string(result).decode();dispose(result)
    runtime=dict(python=sys.version,libclang=clang_version,libclang_sha256=sha(Path(config['libclang'])),
                 packages=subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True))
    atomic(evidence/'runtime.json',runtime)
    with tarfile.open(evidence/'core-5.0.0-source.tar.gz','w:gz') as archive:
        for item in tracked['files']:archive.add(source/item['path'],arcname=item['path'],recursive=False)
        archive.add(source/'license.md',arcname='license.md',recursive=False)
    manifest={str(path.relative_to(evidence)):sha(path) for path in sorted(evidence.rglob('*')) if path.is_file()}
    atomic(evidence/'manifest.json',dict(commit=commit,roles=summary['roles'],files=manifest,
        original_behavior_verified=False,original_arm_abi_verified=False,hardware_verified=False))
    (evidence/'SHA256SUMS').write_text(''.join(digest+'  '+name+'\n' for name,digest in manifest.items()))
    print(json.dumps(dict(evidence=str(evidence),files=len(manifest),skip_entries=len(fragments['functions']),libclang=clang_version)))


if __name__=='__main__':main()
