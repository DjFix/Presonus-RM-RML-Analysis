#!/usr/bin/env python3
"""Remove src/recovered from active code layout; retain a hash-bound move record."""
import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library',type=Path,required=True)
    parser.add_argument('--record',type=Path,required=True)
    args=parser.parse_args()
    library=args.library.resolve()
    record=args.record.resolve()
    record.parent.mkdir(parents=True,exist_ok=True)
    result={'moves':[],'reference_edits':[],'historical_validation_records':'Preserved; affected working seals require replay before readiness.'}
    old=library/'src/recovered'
    if old.exists():
        for source in sorted(old.rglob('*')):
            if not source.is_file():continue
            assert not source.is_symlink(),'unexpected symlink in source tree'
            target=library/'src'/source.relative_to(old)
            original_hash=digest(source)
            target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists():
                assert digest(target)==original_hash,f'different files at migration target: {target}'
                source.unlink()
            else:
                source.rename(target)
            assert digest(target)==original_hash
            result['moves'].append({'from':str(source.relative_to(library)),'to':str(target.relative_to(library)),'sha256':original_hash})
        for directory in sorted((p for p in old.rglob('*') if p.is_dir()),key=lambda p:len(p.parts),reverse=True):
            directory.rmdir()
        old.rmdir()
    candidates=[library/'CMakeLists.txt',library/'README.md']
    candidates+=list((library/'tools').glob('*.py'))
    for path in candidates:
        if path.name=='relocate_sources.py' or path.name.startswith(('core_uc_','extraction_verify_')):continue
        text=path.read_text()
        updated=text.replace('src/recovered/','src/')
        if updated==text:continue
        backup=record.parent/'before'/path.relative_to(library)
        backup.parent.mkdir(parents=True,exist_ok=True)
        if not backup.exists():backup.write_text(text)
        before=digest(path)
        path.write_text(updated)
        result['reference_edits'].append({'path':str(path.relative_to(library)),'before_sha256':before,'after_sha256':digest(path)})
    record.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
