"""Independent payload-byte audit, coverage details, and package I/O inventory."""
from pathlib import Path
import collections
import csv
import hashlib
import itertools
import json
import re

ROOT = Path('/home/rs/projects/opencs/ai-line-analysis')
OUT = ROOT / 'evidence/recovery/2026-10-27/nimh-fpga-decode-01'
B = OUT / 'decoded-final'
SRC = ROOT / 'evidence/recovery/2026-10-27/fpga-identification/mixer-13731'


def save(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2) + '\n')


def rows(name):
    with (B / name).open() as f:
        for line in f:
            yield json.loads(line)


raw = (SRC / 'xmen_nimh_avb_top.bin').read_bytes()
assert hashlib.sha256(raw).hexdigest() == '945b2c3a0f74cd39825ec361da680c92303f20ac7f7a98756b7a829216ef9dbb'
packets = json.loads((SRC / 'xmen_nimh_avb_top.bin.packets.json').read_text())['packets']
fdri = [p for p in packets if p['opcode'] == 2 and p['register'] == 3]
assert len(fdri) == 5 and all(p['type'] == 2 for p in fdri)
payloads = [raw[p['offset'] + 6:p['offset'] + 6 + 2 * p['word_count']] for p in fdri]
for p, data in zip(fdri, payloads):
    assert hashlib.sha256(data).hexdigest() == p['data_sha256']
frames = list(rows('frames.jsonl'))
main = [f for f in frames if f['kind'] == 'main']
bram = [f for f in frames if f['kind'] == 'bram']
iob = next(f for f in frames if f['kind'] == 'iob')
fixups = json.loads((B / 'frame-fixups.json').read_text())
fixby = collections.defaultdict(list)
for f in fixups:
    fixby[f['frame']].append(f)


def frame_bytes(f, initial=False):
    v = int(f['value_hex_msb_first'], 16)
    if initial:
        for bit in fixby[f['index']]:
            assert bool(v >> bit['bit'] & 1) == bit['after']
            v = (v & ~(1 << bit['bit'])) | (int(bit['before']) << bit['bit'])
    return v.to_bytes(f['bits'] // 8, 'big')


# Check all exported data bytes directly against source FDRI payloads. Geometry
# and FAR identities come from Combine; serialization/comparison here is Python.
cursor = 0
dummy = []
for region, group in itertools.groupby(main, key=lambda f: f['region']):
    for f in group:
        data = frame_bytes(f, initial=True)
        assert payloads[0][cursor:cursor + len(data)] == data, ('main', f['index'])
        cursor += len(data)
    dummy.append(dict(region=region, offset_in_fdri=cursor, bytes=260,
                      sha256=hashlib.sha256(payloads[0][cursor:cursor + 260]).hexdigest()))
    cursor += 260  # two dummy frames, 130 bytes each
for f in bram:
    data = frame_bytes(f)
    assert payloads[0][cursor:cursor + len(data)] == data, ('bram', f['index'])
    cursor += len(data)
data = frame_bytes(iob)
assert payloads[0][cursor:cursor + len(data)] == data
cursor += len(data)
assert len(payloads[0]) - cursor == 2
far_to_main = {(f['type'] << 28) | (f['region'] << 24) | (f['major'] << 16) | f['minor']: f for f in main}
fars = [p for p in packets if p['opcode'] == 2 and p['register'] == 1]
assert len(fars) == 5
for far, data in zip(fars[1:], payloads[1:]):
    addr = far['data'][0] << 16 | far['data'][1]
    assert frame_bytes(far_to_main[addr]) == data[:130], ('fixup', addr)
    assert len(data) == 260
save('frame-byte-audit.json', dict(
    status='passed', main_frames_compared=len(main), bram_frames_compared=len(bram),
    iob_bits_compared=iob['bits'], late_frame_writes_compared=4, late_changed_bits=len(fixups),
    region_dummy_frames=dummy, final_fdri_extra_word_hex=payloads[0][cursor:].hex(),
    input_sha256=hashlib.sha256(raw).hexdigest(),
    scope='All initial main/BRAM/IOB frame data and four final main-frame writes match source payload bytes. Padding/extra words recorded, not configuration bits. Does not independently verify database bit meaning, hardware behavior, or CRC algorithm.'))

config = (B / 'configuration-bits.u8').read_bytes()
known = (B / 'decoded-mask.u8').read_bytes()
referenced = (B / 'database-referenced-mask.u8').read_bytes()
coverage = json.loads((B / 'coverage.json').read_text())
assert len(config) == len(known) == len(referenced) == coverage['total_configuration_bits']
assert all(x in (0, 1) for x in config + known + referenced)
assert sum(known) == coverage['decoded_bits']
assert sum(referenced) == coverage['database_referenced_bits']
assert all(not k or r for k, r in zip(known, referenced))
cursor = 0
segments = []
unresolved_set = []
with (OUT / 'per-frame-coverage.jsonl').open('w') as f:
    for row in frames:
        n = row['bits']
        k = known[cursor:cursor+n]
        ref = referenced[cursor:cursor+n]
        data = config[cursor:cursor+n]
        assert int(row['value_hex_msb_first'], 16) == sum(b << i for i, b in enumerate(data))
        entry = {key: val for key, val in row.items() if key != 'value_hex_msb_first'}
        entry.update(decoded_bits=sum(k), referenced_bits=sum(ref), unresolved_bits=n-sum(k),
                     unresolved_set_bits=sum(v and not bit for v, bit in zip(data, k)))
        f.write(json.dumps(entry)+'\n')
        for bit, (v, mk) in enumerate(zip(data, k)):
            if v and not mk:
                unresolved_set.append(dict(kind=row['kind'], frame=row.get('index'), bit=bit,
                    region=row.get('region'), major=row.get('major'), minor=row.get('minor'),
                    global_index=cursor+bit, referenced=bool(ref[bit]), candidate_tiles=[]))
        cursor += n
for tile in rows('tiles.jsonl'):
    for rect in tile['rects']:
        m = re.fullmatch(r'Main\((\d+), (\d+), (\d+), (\d+), (true|false)\)', rect)
        if not m:
            continue
        f0, width, b0, height = map(int, m.groups()[:4])
        for bit in unresolved_set:
            if bit['kind'] == 'main' and f0 <= bit['frame'] < f0+width and b0 <= bit['bit'] < b0+height:
                bit['candidate_tiles'].append(dict(tile=tile['tile'], tile_class=tile['class']))
save('unresolved-set-bits.json', unresolved_set)
issues = list(rows('decoder-issues.jsonl'))
coverage.update(decoded_percent=100*coverage['decoded_bits']/len(config),
                referenced_but_unmatched_bits=sum(referenced)-sum(known),
                not_referenced_bits=len(config)-sum(referenced),
                issue_categories=dict(collections.Counter(r['kind'] for r in issues)),
                final_state='Eight later-write bit changes applied before primitive decode; before/after retained.',
                limitations=['Zero unclassified bits remain unresolved; zero is not proof of an unused or reserved bit.',
                             'Known bit locations and matching field patterns do not prove complete functional or timing equivalence.',
                             'Selected routing fields include defaults; counts are not utilization.',
                             'No source HDL names, original hierarchy, global netlist or hardware behavior recovered.'])
save('coverage-summary.json', coverage)
save('unresolved-fields.json', issues)

io = collections.defaultdict(dict)
classes = collections.Counter()
lut_total = lut_nonzero = 0
lut_examples = []
clock_settings = []
for r in rows('primitive-settings.jsonl'):
    if 'attribute' not in r:
        continue
    classes[r['bel_class']] += 1
    if r['class'] == 'IOB':
        cell = r['tile'].split('.')[0]
        io[(cell, r['bel'])][r['attribute']] = r['value']
    if r['bel_class'] == 'SLICE' and r['attribute'] in ('A6LUT','B6LUT','C6LUT','D6LUT'):
        lut_total += 1
        if int(r['value'], 16):
            lut_nonzero += 1
            if len(lut_examples) < 8:
                lut_examples.append(r)
    if r['bel_class'] in ('PLL','DCM','BUFPLL'):
        clock_settings.append(r)
save('clock-settings.json', clock_settings)
save('primitive-summary.json', dict(attribute_rows_by_class=dict(classes),
    lut_tables_recovered=lut_total, nonzero_lut_tables=lut_nonzero, lut_examples=lut_examples,
    limitation='Nonzero LUT tables and decoded default settings are not a used-resource count.'))
pins=[]
for line in (B/'package-csg324.txt').read_text().splitlines():
    m=re.fullmatch(r'\s*pin (\w+) = (D\d+X\d+Y\d+)\.(IOB\[\d+\])\.PAD;',line)
    if not m:
        continue
    ball, cell, bel = m.groups()
    attrs = io.get((cell,bel),{})
    pins.append(dict(ball=ball,cell=cell,bel=bel,attributes=attrs,
                     output_driver_configured=attrs.get('OUTPUT_ENABLE')=='1',
                     external_net=None,external_net_status='unassigned; photos do not expose BGA ball continuity'))
assert pins and all(p['attributes'] for p in pins)
save('package-io-settings.json', pins)
with (OUT/'package-io-settings.csv').open('w',newline='') as f:
    keys=['ball','cell','bel','output_driver_configured','PULL','IBUF_MODE','PDRIVE','NDRIVE','PSLEW','NSLEW','external_net_status']
    w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
    for p in pins:
        row={k:p[k] for k in keys if k in p}
        row.update({k:p['attributes'].get(k) for k in keys if k not in row})
        w.writerow(row)
save('package-summary.json',dict(package='CSG324',mapped_user_io_balls=len(pins),
    output_driver_configured=sum(p['output_driver_configured'] for p in pins),
    exact_external_net_assignments=0,
    limitation='Output enable is a static configuration field, not proof of runtime drive; BGA connectivity cannot be traced through these top-side photos.'))
print(json.dumps({k:coverage[k] for k in ('decoded_bits','decoded_percent','unresolved_bits','unresolved_set_bits','referenced_but_unmatched_bits')},indent=2))
print('Frame-byte audit passed; package I/O balls',len(pins),'output drivers configured',sum(p['output_driver_configured'] for p in pins))
print('Unresolved set bits',json.dumps(unresolved_set))
