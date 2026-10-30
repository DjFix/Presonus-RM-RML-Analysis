#!/usr/bin/env python3
"""Bind an actual native Core archive/allocator smoke to pinned source hashes."""
import argparse
import hashlib
import io
import json
import subprocess
from pathlib import Path
from elftools.elf.elffile import ELFFile


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True)
    args=parser.parse_args()
    root=args.repository.resolve();evidence=args.evidence.resolve();evidence.mkdir(parents=True,exist_ok=True)
    source=root/'third_party/ccl-framework';archive=root/'temp/core-upstream/build-output/linux/Release/libcorelib.a'
    build_proof=root/'evidence/recovery/2026-10-26/core-upstream/linux-systemdeps-03/validation.json'
    validation=json.loads(build_proof.read_text())
    assert validation['framework_build_passed'] and validation['core_source_files_unchanged']
    commit=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
    assert commit=='e8cbdea4a4a20e15111f5a690798a259c0374b31'
    assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain','--untracked-files=no'],text=True).strip()
    nm=subprocess.check_output(['nm','-g','--defined-only',str(archive)],text=True)
    defined={line.split()[-1] for line in nm.splitlines() if len(line.split())>=3}
    required=['_ZN4Core2IO6BufferC1EPvjb','_ZN4Core2IO6BufferC1Ejb','_ZN4Core2IO6BufferD1Ev',
              '_ZN4Core2IO6Buffer6resizeEj','_ZN4Core2IO6Buffer8copyFromEPKvj']
    assert set(required)<=defined,'Expected actual Core Buffer symbols missing'
    native_object=subprocess.check_output(['ar','p',str(archive),'corebuffer.cpp.o'])
    elf=ELFFile(io.BytesIO(native_object))
    smoke=root/'temp/core-upstream/native-smoke'
    result=subprocess.run([str(smoke)],cwd=root,text=True,capture_output=True)
    (evidence/'smoke.log').write_text(result.stdout+result.stderr)
    assert result.returncode==0 and result.stdout.strip()=='PASS: 18 upstream-native Buffer/clock checks'
    inputs=['core/public/corebuffer.h','core/public/corebuffer.cpp','core/malloc/coremalloc.cpp',
            'core/system/coretime.h','core/platform/shared/posix/coretime.posix.h',
            'core/platform/shared/coreplatformtime.h','core/public/coretypes.h','core/public/coreplatform.h','core/platform/corefeatures.h']
    report=dict(kind='upstream-source-port-native-provider',upstream_commit=commit,native_target='corelib',
        framework_build_passed=True,buffer_clock_smoke_passed=True,buffer_clock_checks=18,
        native_architecture=elf['e_machine'],native_elf_class=elf.elfclass,
        archive=dict(path=str(archive.relative_to(root)),sha256=sha(archive),bytes=archive.stat().st_size),
        actual_defined_mangles=required,
        upstream_inputs={str((source/name).relative_to(root)):sha(source/name) for name in inputs},
        build_proof=dict(path=str(build_proof.relative_to(root)),sha256=sha(build_proof)),
        smoke_source=dict(path='temp/core-upstream/native-smoke.cpp',sha256=sha(root/'temp/core-upstream/native-smoke.cpp')),
        smoke_binary_sha256=sha(smoke),smoke_log_sha256=sha(evidence/'smoke.log'),
        compiler=subprocess.check_output(['g++','--version'],text=True).splitlines()[0],
        formatter=subprocess.check_output([str(root/'uc-library/.venv/bin/clang-format'),'--version'],text=True).strip(),
        formatter_configuration_sha256=sha(root/'.clang-format'),
        consumer_flags=['-std=c++17','-O2','-DNDEBUG','-Ithird_party/ccl-framework'],
        consumer_sources=['third_party/ccl-framework/core/malloc/coremalloc.cpp'],
        consumer_link_flags=['-pthread','-ldl','-lm'],
        test_only_link_flags=['-Wl,--wrap=core_realloc'],
        original_behavior_verified=False,original_arm_abi_verified=False,hardware_verified=False,
        tool_sha256=sha(Path(__file__)))
    (evidence/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(native_architecture=report['native_architecture'],archive_sha256=sha(archive),smoke_passed=True,buffer_symbols=len(required))))


if __name__=='__main__':main()
