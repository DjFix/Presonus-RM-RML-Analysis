#!/usr/bin/env python3
"""Freeze an expanded integration input set before configure/build/CTest."""
import argparse
import hashlib
import json
from pathlib import Path


def apply_relocations(library, previous, names, manifest_path):
    """Explicitly replace retired inputs only with verified preserved move bytes."""
    root = library.parent.resolve()
    manifest_path = manifest_path.resolve()
    if not manifest_path.is_relative_to(root):
        raise ValueError('Relocation manifest outside repository')
    manifest = json.loads(manifest_path.read_text())
    if manifest.get('version') != 1 or not manifest.get('moves'):
        raise ValueError('Versioned nonempty relocation manifest required')
    changes = []
    seen = set()
    for move in manifest['moves']:
        old = (root / move['original_path']).resolve()
        new = (root / move['new_path']).resolve()
        trash = (root / move['trash_path']).resolve()
        if (not old.is_relative_to(library) or not new.is_relative_to(library)
                or not trash.is_relative_to(root / '.trashes')
                or old.exists() or not new.is_file() or not trash.is_file()):
            raise ValueError('Invalid preserved source relocation')
        old_name, new_name = str(old.relative_to(library)), str(new.relative_to(library))
        if old_name in seen or old_name not in previous['files'] or old_name not in names:
            raise ValueError('Duplicate or unbound original relocation: ' + old_name)
        seen.add(old_name)
        old_hash = hashlib.sha256(trash.read_bytes()).hexdigest()
        new_hash = hashlib.sha256(new.read_bytes()).hexdigest()
        if (old_hash != move['sha256'] or old_hash != previous['files'][old_name]
                or new_hash != move['new_sha256'] or trash.stat().st_size != move['size']):
            raise ValueError('Relocation source/destination hash mismatch')
        names.remove(old_name)
        names.add(new_name)
        changes.append(dict(old_path=old_name, new_path=new_name,
                            old_sha256=old_hash, new_sha256=new_hash,
                            trash_path=move['trash_path']))
    return dict(manifest=str(manifest_path.relative_to(root)),
                manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
                changes=changes, previous_provenance_preserved=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library', type=Path, required=True)
    parser.add_argument('--additional', type=Path, action='append', default=[])
    parser.add_argument('--additional-list', type=Path)
    parser.add_argument('--source-relocations', type=Path)
    parser.add_argument('--expected-suites', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    library = args.library.resolve()
    previous = json.loads((library / 'validation/integration.json').read_text())
    names = set(previous['files']) | {str(path) for path in args.additional}
    if args.additional_list:
        extra=json.loads(args.additional_list.read_text())
        if not isinstance(extra,list) or not all(isinstance(name,str) for name in extra):
            raise SystemExit('Additional input list must be a JSON array of paths')
        names.update(extra)
    relocations = (apply_relocations(library, previous, names, args.source_relocations)
                   if args.source_relocations else None)
    files = {}
    for name in sorted(names):
        path = (library / name).resolve()
        if not path.is_relative_to(library) or not path.is_file():
            raise SystemExit(f'Invalid integration input: {name}')
        files[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    report = dict(test_suites=args.expected_suites, files=files)
    if relocations:
        report["source_relocations"] = relocations
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(input_files=len(files), expected_suites=args.expected_suites)))


if __name__ == '__main__':
    main()
