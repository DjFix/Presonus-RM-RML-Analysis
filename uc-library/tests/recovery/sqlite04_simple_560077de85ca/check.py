"""Compare the sealed native fixture with the Linux SimpleController replay."""
import argparse
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).parent
STATE = ('dirty', 'owner', 'rate', 'channel', 'identity')

def run(executable, fixture):
    data = json.loads(fixture.read_text())
    for number, case in enumerate(data['cases']):
        count, lookup, skip, target, null = case['options']
        deleting = data['elf']['mangled'].endswith('D0Ev')
        header = [count, int(lookup), int(skip is not None), skip or 0,
                  int(target), int(null), int(deleting),
                  int('SimpleControllerC2E' in data['elf']['mangled'])]
        lines = [header, *case['operations']]
        commands = '\n'.join(' '.join(map(str, line)) for line in lines) + '\n'
        replay = subprocess.run([str(executable.resolve())], input=commands, check=True,
                                capture_output=True, text=True)
        reported = dict(messages=[])
        for line in replay.stdout.splitlines():
            action, *values = line.split()
            if action == 'message':
                reported['messages'].append(list(map(int, values)))
            elif action == 'state':
                reported.update(zip(STATE, map(int, values), strict=True))
            elif action == 'values':
                reported['values'] = list(map(int, values))
            elif action == 'event':
                reported.setdefault('events', []).extend(values)
            else:
                raise ValueError(line)
        expected = {k: v for k, v in case['actual'].items() if k not in ('pending', 'pending_before_drain')}
        if 'events' in expected:
            reported.setdefault('events', [])
        assert expected == reported, (number, expected, reported)
    print(f"{data['elf']['mangled']}: {len(data['cases'])} matched ARM/Linux cases")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('executable', type=Path)
    parser.add_argument('fixtures', nargs='+', type=Path)
    parser.add_argument('--symbols', action='store_true')
    parser.add_argument('--native', action='store_true')
    args = parser.parse_args()
    for fixture in args.fixtures:
        if args.symbols:
            symbol = json.loads(fixture.read_text())['elf']['mangled']
            output = subprocess.check_output(['nm', '--defined-only', args.executable], text=True)
            assert symbol in {line.split()[-1] for line in output.splitlines() if line.split()}
            print(symbol)
        elif args.native:
            from native import SEALED, generate

            observed = generate(SEALED / fixture.parent.name / 'CONTEXT.json')
            assert json.loads(json.dumps(observed)) == json.loads(fixture.read_text())
            print(f"{observed['elf']['mangled']}: regenerated {len(observed['cases'])} ARM cases")
        else:
            run(args.executable, fixture)
