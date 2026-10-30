"""Append an observed recovery queue event inside project evidence."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', type=Path, required=True)
    parser.add_argument('--phase', required=True)
    parser.add_argument('--candidate', action='append', required=True)
    parser.add_argument('--event', choices=('candidate-ready', 'root-review-start',
                                          'role-audit-finished', 'batch-admitted'), required=True)
    parser.add_argument('--evidence', action='append', default=[], help='Existing repository-relative evidence file')
    args = parser.parse_args()
    repository = args.repository.resolve()
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]*', args.phase):
        parser.error('Phase must be a single safe path component')
    for item in args.evidence:
        path = (repository / item).resolve()
        if Path(item).is_absolute() or not path.is_relative_to(repository) or not path.is_file():
            parser.error('Evidence must be an existing repository-relative file')
    now = datetime.now(timezone.utc)
    record = dict(event=args.event, observed_at=now.isoformat(), phase=args.phase,
                  candidates=args.candidate, evidence=args.evidence,
                  timing='Observation time only; not a reconstructed historical event time')
    output = repository / 'evidence/recovery' / now.date().isoformat() / args.phase / 'queue-events.jsonl'
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('a') as stream:
        stream.write(json.dumps(record) + '\n')
    print(json.dumps(dict(event=args.event, log=str(output.relative_to(repository)))))


if __name__ == '__main__':
    main()
