"""Bind DSP process tables to the host's observed OMAP target IDs."""
import argparse
import json
import re
import struct
from pathlib import Path

from analyze import sha

NAMES = {4: 'limiter', 5: 'gate', 6: 'compressor', 12: 'channel EQ',
         22: 'reverb', 23: 'delay', 30: 'main audio engine'}
EXPECTED = {4: (0x1181ddcc, 0x1181db0a), 5: (0xc709b604, 0xc709b192),
            6: (0xc709fcc4, 0xc709fb32), 12: (0x1181d304, 0x1181cda8),
            22: (0xc708aa60, 0xc7089a20), 23: (0xc7095b44, 0xc7095978),
            30: (0xc7091224, 0xc708dfa0)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--evidence', type=Path, required=True)
    args = ap.parse_args()
    path = args.evidence
    inputs = {}
    listings = {}
    indexed = {}
    for label in ('text', 'fasttext'):
        file = path / (label + '.gnu.asm')
        inputs[file.name] = sha(file.read_bytes())
        lines = file.read_text().splitlines()
        listings[file.name] = lines
        for number, line in enumerate(lines):
            match = re.match(r'^([0-9a-f]+):', line)
            if match:
                indexed[int(match[1], 16)] = (file.name, number)

    def context(address, count=12):
        file, idx = indexed[address]
        return dict(listing=file, line=idx + 1, instructions=listings[file][idx:idx + count])

    def window(address, end):
        return [line for va, (file, idx) in sorted(indexed.items()) if address <= va < end
                for line in [listings[file][idx]]]

    def code(address):
        return 0xc7087800 <= address < 0xc70a9180 or 0x11818600 <= address < 0x1181e360

    const = (path / 'segment-02-c70c2180.bin').read_bytes()
    tables = []
    for off in range(0, len(const) - 152, 8):
        if const[off:off + 8] != b'\0' * 8:
            continue
        entries = []
        pos = off + 8
        while pos + 8 <= len(const):
            adjustment, function = struct.unpack_from('<II', const, pos)
            if adjustment or not code(function):
                break
            entries.append(function)
            pos += 8
        if len(entries) < 17:
            continue
        accessor = entries[10]  # independently checked short return-constant methods
        type_id = None
        for line in window(accessor, accessor + 8):
            match = re.search(r'\bmvk\s+\.[LS]\d\s+(\d+),a4', line)
            if match:
                type_id = int(match[1])
                break
        tables.append(dict(address=hex(0xc70c2180 + off), payload_offset=hex(off),
                           bytes_sha256=sha(const[off:pos]), size=pos - off,
                           entries=[dict(offset=hex(8 + i * 8), adjustment=0, function=hex(fn))
                                    for i, fn in enumerate(entries)],
                           type_accessor=hex(accessor), observed_type_id=type_id,
                           property_handler=hex(entries[0]), audio_callback=hex(entries[3])))
    trampolines = {}
    for va in range(0xc70a8e80, 0xc70a9180, 32):
        lines = window(va, va + 24)
        low = high = None
        for line in lines:
            match = re.search(r'\b(mvk|mvkh)\s+\.S2\s+(-?\d+),b10', line)
            if match:
                if match[1] == 'mvk':
                    low = int(match[2]) & 0xffff
                else:
                    high = int(match[2]) & 0xffff0000
        if low is not None and high is not None and any('b .S2 b10' in l for l in lines):
            trampolines[hex(va)] = dict(destination=hex(high | low), evidence=context(va, 7))
    all_functions = sorted({int(e['function'], 16) for t in tables for e in t['entries']})
    mapped = []
    for type_id, (handler, callback) in EXPECTED.items():
        found = [t for t in tables if t['observed_type_id'] == type_id
                 and int(t['property_handler'], 16) == handler and int(t['audio_callback'], 16) == callback]
        assert len(found) == 1, (type_id, found)
        table = found[0]
        stop = min((fn for fn in all_functions if fn > callback), default=callback + 4096)
        sample_lines = window(callback, stop)
        thunk_calls = []
        for line in sample_lines:
            for address, target in trampolines.items():
                if re.search(r'\b' + re.escape(address) + r'\b', line):
                    thunk_calls.append(dict(instruction=line, trampoline=address, destination=target['destination']))
        dest = path / f'process-{type_id:02d}-audio-window.asm'
        dest.write_text('; Analyst-labelled callback window. End is next table-referenced address, not original function size.\n'
                        + '\n'.join(sample_lines) + '\n')
        mapped.append(dict(type_id=type_id, analyst_label=NAMES[type_id], original_DSP_class_name='unavailable',
                           table=table, type_accessor_evidence=context(int(table['type_accessor'], 16), 4),
                           property_handler_evidence=context(handler, 20), audio_callback_evidence=context(callback, 24),
                           callback_window=dict(start=hex(callback), end=hex(stop), file=dest.name, sha256=sha(dest.read_bytes())),
                           fast_kernel_trampoline_edges=thunk_calls))
    # Main-engine dispatch through vtable function pointer at +36 (slot at +32,
    # adjustment at +32, callable address at +36); paired adjustment load at +32.
    dispatch = []
    for va, (file, idx) in sorted(indexed.items()):
        line = listings[file][idx]
        if 0xc708dfa0 <= va < 0xc7091000 and re.search(r'\bldw\b.*\(36\)', line):
            dispatch.append(dict(address=hex(va), evidence=dict(listing=file, line=max(1, idx - 5),
                                                               instructions=listings[file][max(0, idx - 6):idx + 11])))
    report = dict(elf_sha256=json.loads((path/'manifest.json').read_text())['elf_sha256'],
                  script_sha256=sha(Path(__file__).read_bytes()), inputs=inputs,
                  const_sha256=sha(const), table_layout='observed 8-byte zero header, then (adjustment, function) pairs',
                  discovered_tables=tables, mapped_processes=mapped, trampolines=trampolines,
                  main_engine_dispatch_candidates=dispatch,
                  limits='Static host target-ID/table/handler/callback binding. No original DSP names, complete algorithm reconstruction, runtime activation or hardware equivalence claimed.')
    (path / 'process-map.json').write_text(json.dumps(report, indent=2) + '\n')
    print('tables', len(tables), 'mapped process types', len(mapped), 'trampolines', len(trampolines))
    for row in mapped:
        print(row['type_id'], row['analyst_label'], row['table']['address'], row['table']['property_handler'], row['table']['audio_callback'],
              sorted({e['destination'] for e in row['fast_kernel_trampoline_edges']}))


if __name__ == '__main__':
    main()
