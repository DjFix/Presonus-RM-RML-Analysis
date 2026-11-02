import argparse
import json
import subprocess

p = argparse.ArgumentParser()
p.add_argument('--executable', required=True)
p.add_argument('--fixtures', required=True)
a = p.parse_args()
fixtures = json.load(open(a.fixtures))
assert len(fixtures['lifecycle']) == len(fixtures['cases'])
for case in fixtures['lifecycle']:
    assert case['getter_returned_injected_pointer'] and case['pointer_unchanged']
    assert case['calls'] == [{'target': 'Core::Portable::Component::~Component()', 'this': 0}]
    assert [write['offset'] for write in case['writes']] == [0, 4]
for case in fixtures['cases']:
    assert case['returned_this']
    assert case['calls'] == [{'target': 'Core::Portable::Component::Component(char const*)', 'this': 0, 'name_pointer': 0}]
    assert next(w for w in case['writes'] if w['offset'] == 132)['value'] == 0
    # Actual host provider execution is separate from the native boundary.
    result = json.loads(subprocess.check_output([a.executable, case['variant'], str(case['fill']), case['name']], text=True))
    assert result == {'original_null': True, 'provider_state': True, 'referent_survives': True}
print(json.dumps({'passed': len(fixtures['cases']), 'domain': fixtures['domain'], 'host_provider': 'actual pinned CCL, not original ARM Core execution'}))
