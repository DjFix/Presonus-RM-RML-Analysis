"""Evidence-bound declaration assessments, separate from readiness admission."""
from contextlib import closing
import argparse
import datetime
import hashlib
import json
from pathlib import Path

import adapter
import orm
import schema

ROOT = Path(__file__).resolve().parents[3]
STATUS = 'return_type_unresolved'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assess(database, audit_path, apply=False):
    audit_path = audit_path.resolve()
    audit = json.loads(audit_path.read_text())
    evidence = {'audit': {'path': str(audit_path.relative_to(ROOT)), 'sha256': sha(audit_path)},
                'inputs': audit['evidence']}
    for item in evidence['inputs'].values():
        if sha(ROOT / item['path']) != item['sha256']:
            raise ValueError('Audit input changed: ' + item['path'])
    selected = []
    with closing(orm.Unit(database, write=apply)) as unit:
        schema.require_current(unit.raw)
        for name, entry in audit['per_unique_name'].items():
            if (entry['method_kind'], entry['decision']) != ('ordinary_method', 'independent_original_declaration_missing'):
                continue
            for identity in entry['identities']:
                record = unit.session.query(orm.Record).filter_by(
                    elf=identity['original_elf_sha256'], mangled=name).one()
                if record.status != 'pending':
                    continue
                meta = json.loads(record.metadata_json)
                proof_hash = meta['validation_sha256']
                if sha(ROOT / 'uc-library' / meta['validation']) != proof_hash:
                    raise ValueError('Current proof changed: ' + name)
                prior = unit.session.query(orm.DeclarationAssessment).filter_by(
                    record_id=record.id, proof_sha256=proof_hash).one_or_none()
                if prior:
                    if prior.declaration_status != STATUS:
                        raise ValueError('Conflicting assessment: ' + name)
                    continue
                if not entry['concrete_missing_evidence'].strip():
                    raise ValueError('Specific missing evidence required')
                item = dict(record_id=record.id, proof_sha256=proof_hash,
                    declaration_status=STATUS, reason=entry['concrete_missing_evidence'],
                    portable_return=entry['portable_return'],
                    evidence_json=json.dumps(evidence, sort_keys=True),
                    assessed_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
                selected.append({'elf': record.elf, 'mangled': name, **item})
                if apply:
                    unit.session.add(orm.DeclarationAssessment(**item))
        if sha(audit_path) != evidence['audit']['sha256']:
            raise ValueError('Audit changed during assessment')
        for item in evidence['inputs'].values():
            if sha(ROOT / item['path']) != item['sha256']:
                raise ValueError('Audit evidence changed during assessment')
        if apply:
            unit.commit()
    return {'applied': apply, 'identities': len(selected),
            'unique_names': len({r['mangled'] for r in selected}), 'records': selected}


def summary(database):
    with closing(orm.Unit(database)) as unit:
        schema.require_current(unit.raw)
        rows = unit.raw.execute("SELECT declaration_status, count(*) identities, count(DISTINCT mangled) names FROM symbol_declaration_status WHERE readiness_status='pending' GROUP BY declaration_status ORDER BY declaration_status").fetchall()
        return [dict(r) for r in rows]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--registry-db', type=Path)
    p.add_argument('--audit', type=Path)
    p.add_argument('--apply', action='store_true')
    a = p.parse_args()
    if a.apply and not a.audit:
        p.error('--apply requires --audit')
    db = adapter.resolve_db(ROOT / 'uc-library', a.registry_db)
    print(json.dumps(assess(db, a.audit, a.apply) if a.audit else summary(db), indent=2))


if __name__ == '__main__':
    main()
