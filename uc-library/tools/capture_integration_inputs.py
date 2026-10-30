#!/usr/bin/env python3
"""Freeze an expanded integration input set before configure/build/CTest."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library', type=Path, required=True)
    parser.add_argument('--additional', type=Path, action='append', default=[])
    parser.add_argument('--additional-list', type=Path)
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
    files = {}
    for name in sorted(names):
        path = (library / name).resolve()
        if not path.is_relative_to(library) or not path.is_file():
            raise SystemExit(f'Invalid integration input: {name}')
        files[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    report = dict(test_suites=args.expected_suites, files=files)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(input_files=len(files), expected_suites=args.expected_suites)))


if __name__ == '__main__':
    main()
