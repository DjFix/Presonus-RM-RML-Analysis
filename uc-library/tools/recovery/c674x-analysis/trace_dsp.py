"""Normalize GNU C674x constants and retain bounded dispatch/kernel evidence."""
import argparse
import collections
import json
import re
import struct
from pathlib import Path

from analyze import sha

TAGS = ['comp', 'gate', 'lim ', 'mbqd', 'iir4', 'mprm', 'mpro', 'Para', 'Pari',
        '2Par', 'aesp', 'meng', 'shsp', 'metr', 'mter', 'spct', 'Setu', 'Setup']
LINE = re.compile(r'^([0-9a-f]+):\s+([0-9a-f]{4,8})\s+(.*)$')
LOAD = re.compile(r'\b(mvk|mvkh)\s+\.[A-Z]\d\s+(-?(?:0x[0-9a-f]+|\d+)),([ab]\d+)')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--evidence', type=Path, required=True)
    ap.add_argument('--objdump', type=Path, required=True)
    args = ap.parse_args()
    import subprocess
    path = args.evidence
    manifest = json.loads((path / 'manifest.json').read_text())
    version = subprocess.run([str(args.objdump), '--version'], capture_output=True, text=True, check=True).stdout.splitlines()[0]
    selected = [('segment-04-c7087800.bin', 'text'), ('segment-09-11818600.bin', 'fasttext'),
                ('segment-05-80000000.bin', 'startup')]
    tags = {int.from_bytes(tag.encode(), 'big'): tag for tag in TAGS if len(tag) == 4}
    constants = []
    branches = []
    counts = {}
    listings = {}
    instruction_rows = []
    for filename, label in selected:
        row = next(r for r in manifest['segments'] if r['filename'] == filename)
        command = [str(args.objdump), '-D', '-b', 'binary', '-m', 'tic6x', '-EL',
                   '--adjust-vma=' + row['destination_va'], str(path / filename)]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        dest = path / (label + '.gnu.asm')
        dest.write_text(result.stdout)
        listings[label] = dict(command=command, sha256=sha(dest.read_bytes()), stderr=result.stderr)
        lines = result.stdout.splitlines()
        regs = {}
        counters = collections.Counter()
        for number, line in enumerate(lines):
            match = LINE.match(line)
            if not match:
                continue
            va = int(match[1], 16)
            text = match[3]
            normalized = re.sub(r'^\|\|\s*', '', text)
            normalized = re.sub(r'^\[[^]]+\]\s*', '', normalized)
            opcode = normalized.split()[0] if normalized else ''
            counters[opcode] += 1
            instruction_rows.append(dict(address=hex(va), text=text, listing=dest.name, line=number + 1))
            load = LOAD.search(text)
            if load:
                op, value, reg = load.groups()
                value = int(value, 0)
                if op == 'mvk':
                    regs[reg] = (value & 0xffffffff, va)
                elif reg in regs and va - regs[reg][1] <= 64:
                    combined = (value & 0xffff0000) | (regs[reg][0] & 0xffff)
                    if combined in tags:
                        constants.append(dict(address=hex(va), low_instruction=hex(regs[reg][1]),
                                              value=hex(combined), tag=tags[combined], register=reg,
                                              listing=dest.name, line=number + 1,
                                              context=lines[max(0, number - 4):number + 9],
                                              status='constant construction candidate; review control flow'))
                    regs[reg] = (combined, va)
            branch = re.search(r'\b(b|bnop|callp)\s+\.[A-Z]\dX?\s+(0x[0-9a-f]+)', text)
            if branch:
                branches.append(dict(instruction=hex(va), target=branch[2], opcode=branch[1], listing=dest.name))
        counts[label] = dict(counters)
    (path / 'dsp-instructions.json').write_text(json.dumps(instruction_rows, indent=2) + '\n')
    # TI COFF-style .cinit table: 32-bit length, destination, payload padded to 8.
    # Accept only if every record and terminating/padding byte is accounted for.
    data = (path / 'segment-00-c70c3960.bin').read_bytes()
    records = []
    cursor = 0
    cinit_valid = True
    while cursor + 4 <= len(data):
        size = struct.unpack_from('<I', data, cursor)[0]
        if not size:
            cinit_valid = not any(data[cursor:])
            break
        if cursor + 8 + size > len(data):
            cinit_valid = False
            break
        va = struct.unpack_from('<I', data, cursor + 4)[0]
        payload = data[cursor + 8:cursor + 8 + size]
        records.append(dict(offset=hex(cursor), destination=hex(va), size=size, sha256=sha(payload),
                            words=[hex(x[0]) for x in struct.iter_unpack('<I', payload[:len(payload)//4*4])]))
        cursor = (cursor + 8 + size + 7) & ~7
    report = dict(elf_sha256=manifest['elf_sha256'], tool=version,
                  tool_sha256=sha(args.objdump.read_bytes()), script_sha256=sha(Path(__file__).read_bytes()),
                  listings=listings, instruction_counts=counts, property_constants=constants,
                  direct_branches=branches, cinit=dict(format_hypothesis='TI COFF 32-bit length/address; 8-byte aligned records',
                                                       fully_accounted=cinit_valid, records=records),
                  limits='Static candidates; no native execution, no full control-flow graph, data can decode as instructions')
    (path / 'dsp-trace.json').write_text(json.dumps(report, indent=2) + '\n')
    print(version)
    print('message constant matches:', [(r['tag'], r['address']) for r in constants])
    print('cinit records:', len(records), 'fully accounted:', cinit_valid)
    for label, counter in counts.items():
        print(label, 'MPYSP', counter.get('mpysp', 0), 'ADDSP', counter.get('addsp', 0),
              'unknown', counter.get('.word', 0), 'compact packet headers', counter.get('<fetch', 0))


if __name__ == '__main__':
    main()
