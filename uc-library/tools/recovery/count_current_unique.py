"""Compatibility entrypoint for canonical SQLite symbol statistics.

The former fixed-workload JSON schema is retired. Output uses the same tables
and exact-name semantics as symbol_statistics.py, including provider exclusions.
"""
import argparse
import json
from pathlib import Path
from symbol_statistics import build_report, resolve_db


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument('--registry-db', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = build_report(resolve_db(args.repository.resolve() / 'uc-library', args.registry_db))
    text = json.dumps(result, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x') as stream:
            stream.write(text)
    print(text, end='')


if __name__ == '__main__':
    main()
