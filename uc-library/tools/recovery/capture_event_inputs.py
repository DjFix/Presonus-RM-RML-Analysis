import hashlib
import json
from pathlib import Path

library = Path('uc-library')
prior = json.loads((library / 'validation/integration.json').read_text())
names = list(prior['files']) + [
    'src/Presonus/UC/events.cpp',
    'include/presonus/uc/events.hpp',
    'tests/uc_event_tests.cpp',
    'validation/uc-events/arm-vectors.bin',
    'src/Presonus/UC/transport_events.cpp',
    'include/presonus/uc/transport_events.hpp',
    'tests/uc_transport_tests.cpp',
    'validation/uc-transport/arm-vectors.bin',
    'src/embedded_dice/mix.cpp',
    'include/presonus/embedded_dice/mix.hpp',
    'validation/dice-image/mix_differential.cpp',
    'tools/dice_image_mix_replay.py',
    'validation/dice-image/mix-runs/20261026T200643.844086Z/arm-oracle.json',
    'validation/dice-image/mix-runs/20261026T200643.844086Z/arm-fixtures.txt',
    'validation/dice-image/mix-runs/20261026T200643.844086Z/exact-traces.txt.gz',
]
report = dict(test_suites=10, files={
    name: hashlib.sha256((library / name).read_bytes()).hexdigest()
    for name in names
})
(library / 'validation/integration-event-inputs.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(dict(input_files=len(report['files']), expected_suites=10)))
