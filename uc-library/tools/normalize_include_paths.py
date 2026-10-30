#!/usr/bin/env python3
"""Normalize active include paths without rewriting historical validation evidence."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library',type=Path,required=True)
    parser.add_argument('--record',type=Path,required=True)
    args=parser.parse_args()
    library=args.library.resolve()
    record=args.record.resolve()
    if record.exists():raise SystemExit('Refusing to overwrite an existing migration record')
    record.parent.mkdir(parents=True,exist_ok=True)
    replacements={
        'presonus/dice_recovered/':'presonus/dice/',
        'presonus/mixer_dsp_recovered/':'presonus/mixer_dsp/',
        'presonus/surface_panel_recovered/':'presonus/surface_panel/',
        'presonus/core_uc_recovered/':'presonus/core_uc/',
        'presonus/uc/recovered_abi32.hpp':'presonus/uc/abi32.hpp',
    }
    report={'moves':[],'reference_edits':[],'historical_evidence':'unchanged; replay/reseal required for working readiness'}
    for old,new in replacements.items():
        source=library/'include'/old
        destination=library/'include'/new
        if not source.exists():continue
        assert not destination.exists(),f'include migration target already exists: {destination}'
        before={str(p.relative_to(source)):sha(p) for p in source.rglob('*') if p.is_file()} if source.is_dir() else {'':sha(source)}
        destination.parent.mkdir(parents=True,exist_ok=True)
        source.rename(destination)
        after={str(p.relative_to(destination)):sha(p) for p in destination.rglob('*') if p.is_file()} if destination.is_dir() else {'':sha(destination)}
        assert before==after,'include contents changed during move'
        report['moves'].append({'from':'include/'+old,'to':'include/'+new,'files':after})
    candidates=[library/'CMakeLists.txt',library/'README.md']
    for directory in ('include','src','tests'):
        candidates.extend(p for p in (library/directory).rglob('*') if p.is_file() and p.suffix in ('.cpp','.hpp','.h'))
    candidates.extend((library/'tools').glob('*.py'))
    for path in candidates:
        if path.name=='normalize_include_paths.py':continue
        text=path.read_text()
        updated=text
        for old,new in replacements.items():updated=updated.replace(old,new)
        if text==updated:continue
        before=sha(path)
        backup=record.parent/'before'/path.relative_to(library)
        backup.parent.mkdir(parents=True,exist_ok=True)
        backup.write_text(text)
        path.write_text(updated)
        report['reference_edits'].append({'path':str(path.relative_to(library)),'before_sha256':before,'after_sha256':sha(path)})
    record.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
