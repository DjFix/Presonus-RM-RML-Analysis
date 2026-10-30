#!/usr/bin/env python3
"""Bind an integrated CTest result to previously recorded, unchanged inputs."""
import argparse
import hashlib
import json
import re
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library', type=Path, required=True)
    parser.add_argument('--repository', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--platform', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--baseline', type=Path)
    args = parser.parse_args()
    library = args.library.resolve()
    repository = args.repository.resolve()
    evidence = args.evidence.resolve()
    baseline = json.loads((args.baseline or library / 'validation/integration.json').read_text())
    for name, expected in baseline['files'].items():
        if digest(library / name) != expected:
            raise SystemExit(f'Integrated input changed: {name}; rebuild and record new inputs first')
    log = evidence / 'tests.log'
    match = re.search(r'^100% tests passed(?:, 0 tests failed)? out of (\d+)\s*$',
                      log.read_text(), re.MULTILINE)
    if match is None or int(match[1]) != baseline['test_suites']:
        raise SystemExit('CTest log does not prove the expected suite count')
    report = dict(platform=args.platform, ctest_passed=True,
                  test_suites=int(match[1]), files=baseline['files'],
                  test_log=str(log.relative_to(repository)), test_log_sha256=digest(log),
                  logs={str(path.relative_to(repository)): digest(path)
                        for path in (evidence / 'configure.log', evidence / 'build.log', log)},
                  hardware_verified=False)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    (evidence / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(platform=args.platform, test_suites=int(match[1]),
                          input_files=len(report['files']), inputs_unchanged=True)))


if __name__ == '__main__':
    main()
