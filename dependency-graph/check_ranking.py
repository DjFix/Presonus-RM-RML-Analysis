"""Read-only real-corpus checks plus explicitly isolated synthetic state events."""
import argparse
import hashlib
import json
import pathlib
import sqlite3
import time

import ranking as r


def run(db, out):
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    checker_hash = r.digest(__file__)
    ranker_hash = r.digest(r.__file__)
    c = r.ro(db)
    r.check_inputs(c)
    items = [dict(x) for x in c.execute('SELECT i.*,e.queue,e.rank FROM items i JOIN evaluations e USING(id) ORDER BY i.id')]
    for x in items:
        x['features'] = json.loads(x['features']); x['identities'] = json.loads(x['identities'])
        x['rank'] = json.loads(x['rank'])
    calls = {x[0] for x in c.execute("SELECT consumer FROM requirements WHERE scope='callable_behavior'")}
    checks = {
        'arithmetic_leaf': lambda x: x['id'] not in calls and x['features'].get('cfg_complete', {}).get('value') and not x['features'].get('memory_reads', {}).get('value') and not x['features'].get('memory_writes', {}).get('value'),
        'direct_calls': lambda x: x['id'] in calls,
        'explicit_memory_access_not_proven_state': lambda x: bool(x['features'].get('memory_writes', {}).get('value')),
        'partial_cfg': lambda x: x['features'].get('cfg_complete', {}).get('value') is False,
        'aliases_or_grouped_originals': lambda x: len(x['identities']) > 1,
        'multiple_binary_releases': lambda x: len({(y['elf_sha256'], z['firmware_version']) for y in x['identities'] for z in y['releases']}) > 1,
        'core_provider': lambda x: x['original_kind'].startswith('provider') and any(y['provider_id'] for y in x['identities']),
        'known_data_extent': lambda x: x['features']['subject_kind']['value'] == 'data' and x['features']['byte_count']['value'],
        'unknown_extent': lambda x: x['features']['byte_count']['state'] == 'unknown',
        'named_vtable_candidate_not_dispatch_proof': lambda x: any(y['original_mangled'].startswith('_ZTV') for y in x['identities']),
        'nobits_no_fake_content_hash': lambda x: x['features']['storage']['value'] == 'NOBITS',
        'initializer': lambda x: x['features']['subject_kind']['value'] == 'initializer',
        'book_existing_control': lambda x: any('Book' in y['demangled'] for y in x['identities']) and x['queue'] == 'completed',
        'pending_existing_control': lambda x: x['queue'] == 'completed' and x['original_kind'] == 'reconstruct'
    }
    samples = {}
    for name, predicate in checks.items():
        selected = [x for x in items if predicate(x)]
        samples[name] = {'matches': len(selected), 'observation': selected[0] if selected else None, 'absent': not bool(selected)}
    identities = {y['id'] for x in items for y in x['identities']}
    inventory = json.loads(c.execute("SELECT value FROM meta WHERE key='inventory'").fetchone()[0])
    catalog_ids = {x[0] for x in c.execute('SELECT id FROM original_catalog')}
    assert len(catalog_ids) == inventory['occurrences'], 'original identities lost'
    assert identities <= catalog_ids, 'work member absent from complete original catalog'
    # Re-read real ELF section maps independently of native feature construction.
    from elftools.elf.elffile import ELFFile
    binaries, range_checks = {}, []
    for sample in samples.values():
        if not sample['observation']:
            continue
        for original in sample['observation']['identities'][:2]:
            path = r.ROOT / original['releases'][0]['original_path']
            if str(path) not in binaries:
                assert r.digest(path) == original['elf_sha256']
                stream = path.open('rb'); elf = ELFFile(stream)
                symbols = {(s.name, s['st_value'], s['st_size'], str(s['st_shndx']), s['st_info']['type']): s for s in elf.get_section_by_name('.symtab').iter_symbols()}
                binaries[str(path)] = (stream, elf, symbols)
            stream, elf, symbols = binaries[str(path)]
            section = original.get('range', {}).get('section_index') if original.get('range') else original['section_index']
            symbol = symbols.get((original['original_mangled'], original['original_address'], original['original_size'], str(section), original['symbol_kind']))
            assert symbol is not None, 'real symbol/range/section/type absent'
            row = {'elf': original['elf_sha256'], 'mangled': symbol.name, 'address': symbol['st_value'], 'size': symbol['st_size'], 'section_index': symbol['st_shndx']}
            if isinstance(symbol['st_shndx'], int) and symbol['st_size']:
                section = elf.get_section(symbol['st_shndx']); row['section'] = section.name
                address = symbol['st_value'] & ~1 if symbol['st_info']['type'] == 'STT_FUNC' else symbol['st_value']
                assert section['sh_addr'] <= address < address+symbol['st_size'] <= section['sh_addr']+section['sh_size']
                if section['sh_type'] == 'SHT_NOBITS':
                    row.update(storage='NOBITS', file_offset=None, content_sha256=None)
                else:
                    offset = section['sh_offset'] + address-section['sh_addr']
                    stream.seek(offset); content = stream.read(symbol['st_size'])
                    assert len(content) == symbol['st_size']
                    row.update(file_offset=offset, content_sha256=hashlib.sha256(content).hexdigest())
            range_checks.append(row)
    for stream, _, _ in binaries.values():
        stream.close()
    # Real-corpus sized isolated state DB. Production claims/readiness untouched.
    isolated = out / 'isolated.sqlite'
    clone = sqlite3.connect(isolated); clone.row_factory = sqlite3.Row
    c.backup(clone)
    baseline_states = [tuple(x) for x in clone.execute('SELECT * FROM states')]
    baseline_reqs = [tuple(x) for x in clone.execute('SELECT id,evidence,satisfied FROM requirements')]
    evidence_path = out / 'SYNTHETIC-STATE-INPUT.json'
    evidence_path.write_text(json.dumps({'scope': 'Isolated event algorithm tests on real corpus graph. These attestations are synthetic; no production native/provider/data behavior proof.'})+'\n')
    evidence = {'path': str(evidence_path.relative_to(r.ROOT)), 'sha256': r.digest(evidence_path), 'domain': 'synthetic isolated state event; not real dependency admission'}
    event_results = []
    callable_req = clone.execute("SELECT * FROM requirements WHERE scope='callable_behavior' AND target IN (SELECT id FROM states) LIMIT 1").fetchone()
    data_req = clone.execute("SELECT * FROM requirements WHERE scope='representation' LIMIT 1").fetchone()
    assert callable_req and data_req
    completion_target = callable_req['target']
    for label in ('completion', 'provider_binding', 'demotion_revision', 'data_interpretation', 'claim'):
        with clone:
            clone.executemany('UPDATE states SET canonical=?,claimed=?,revision=? WHERE id=?', [(x[1], x[2], x[3], x[0]) for x in baseline_states])
            clone.executemany('UPDATE requirements SET evidence=?,satisfied=? WHERE id=?', [(x[1], x[2], x[0]) for x in baseline_reqs])
            r.reevaluate(clone)
        req = data_req if label == 'data_interpretation' else callable_req
        if label == 'demotion_revision':
            with clone:
                clone.execute('UPDATE requirements SET satisfied=1,evidence=? WHERE id=?', (r.packed(evidence), req['id']))
                r.reevaluate(clone)
        target = req['target'] if label in ('provider_binding', 'data_interpretation', 'demotion_revision') else completion_target
        change = {'item': target, 'expected_revision': 'baseline'}
        if label == 'completion': change['canonical'] = 'completed'
        elif label == 'claim': change['claimed'] = 1
        else: change['requirements'] = [{'id': req['id'], 'satisfied': label != 'demotion_revision', 'evidence': evidence}]
        receipt = r.event(clone, {'id': 'isolated-'+label, 'changes': [change]})
        incremental = [tuple(x) for x in clone.execute('SELECT * FROM evaluations ORDER BY id')]
        with clone:
            clone.execute('DELETE FROM evaluations'); r.reevaluate(clone)
        rebuilt = [tuple(x) for x in clone.execute('SELECT * FROM evaluations ORDER BY id')]
        assert incremental == rebuilt, label+' incremental/full mismatch'
        assert r.static_digest(clone) == r.static_digest(c), 'static facts changed by scoped event'
        event_results.append({'event': label, 'scope': 'isolated synthetic state applied to real graph', 'receipt': receipt, 'all_evaluations_compared': len(incremental), 'equal': True})
    negative_checks = {}
    clone.execute("UPDATE items SET features='corrupted' WHERE id=(SELECT id FROM items LIMIT 1)")
    try:
        r.check_inputs(clone)
        raise AssertionError('corrupt static features accepted')
    except ValueError as error:
        assert 'corruption' in str(error); negative_checks['static_content_corruption'] = str(error)
    finally:
        clone.rollback()
    saved_policy = r.POLICY
    r.POLICY = out / 'changed-policy.json'; r.POLICY.write_text(saved_policy.read_text()+'\n')
    try:
        r.check_inputs(c)
        raise AssertionError('changed policy accepted')
    except ValueError as error:
        assert 'policy changed' in str(error); negative_checks['policy_revision'] = str(error)
    finally:
        r.POLICY = saved_policy
    try:
        clone.execute('INSERT INTO items SELECT * FROM items LIMIT 1')
        raise AssertionError('duplicate unique work accepted')
    except sqlite3.IntegrityError:
        negative_checks['duplicate_unique_work'] = 'rejected by primary key'
    finally:
        clone.rollback()
    assert r.digest(__file__) == checker_hash and r.digest(r.__file__) == ranker_hash, 'producer changed during validation'
    r.check_inputs(c)
    result = {'checker_sha256': checker_hash, 'ranking_producer_sha256': ranker_hash,
              'input_database': str(pathlib.Path(db).resolve().relative_to(r.ROOT)), 'input_static_digest': r.static_digest(c),
              'real_original_occurrences': len(catalog_ids), 'work_member_occurrences': len(identities), 'sample_checks': samples, 'elf_range_checks': range_checks,
              'negative_checks': negative_checks,
              'incremental_vs_full': event_results, 'seconds': time.monotonic()-started,
              'limitations': ['Full evaluator rebuild, not independent semantic verification of synthetic attestations',
                             'Real data table/address candidates remain untyped; no runtime dispatch/initializer-order proof',
                             'No reconstruction worker, readiness admission or production claim mutation']}
    (out / 'VALIDATION.json').write_text(json.dumps(result, indent=2)+'\n')
    return {'samples': {k: v['matches'] for k, v in samples.items()}, 'original_occurrences': len(catalog_ids), 'work_member_occurrences': len(identities), 'event_checks': len(event_results), 'seconds': result['seconds']}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--db', required=True); p.add_argument('--out', type=pathlib.Path, required=True)
    a = p.parse_args(); print(json.dumps(run(a.db, a.out), indent=2))
