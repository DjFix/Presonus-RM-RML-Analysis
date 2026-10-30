"""Offline ELF32 FPGA extraction and bounded Spartan-6 packet inspection.

Not a logic decoder or device programming utility. Standard library only.
Packet definitions: AMD/Xilinx UG380, tables 5-24 through 5-30.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import platform
import struct


def sha(data):
    return hashlib.sha256(data).hexdigest()


def packets(raw):
    sync = raw.index(bytes.fromhex('aa995566'))
    assert sync % 2 == 0 and len(raw) % 2 == 0
    words = struct.unpack('>' + 'H' * ((len(raw) - sync - 4) // 2), raw[sync + 4:])
    result = []
    i = 0
    while i < len(words):
        start = i
        h = words[i]
        i += 1
        typ, op, reg = h >> 13, (h >> 11) & 3, (h >> 5) & 63
        assert typ in (1, 2), (hex(sync + 4 + start * 2), hex(h))
        assert op in (0, 2), (start, op)
        count = h & 31
        if typ == 2:
            assert i + 2 <= len(words)
            count = (words[i] << 16) | words[i + 1]
            i += 2
        assert i + count <= len(words), (start, count)
        payload = raw[sync + 4 + i * 2:sync + 4 + (i + count) * 2]
        row = dict(offset=sync + 4 + start * 2, header=hex(h), type=typ,
                   opcode=op, register=reg, word_count=count,
                   data_sha256=sha(payload))
        if count <= 16:
            row['data'] = list(words[i:i + count])
        i += count
        if typ == 2 and reg == 3 and op == 2:
            # FDRI body is followed by an unpacketized 32-bit AUTO CRC.
            assert i + 2 <= len(words)
            row['auto_crc_not_validated'] = hex((words[i] << 16) | words[i + 1])
            i += 2
        result.append(row)
    ids = [((r['data'][0] << 16) | r['data'][1]) for r in result
           if r['opcode'] == 2 and r['register'] == 14 and r['word_count'] == 2]
    ctls = [r['data'][0] for r in result if r['opcode'] == 2 and r['register'] == 6]
    cmds = [r['data'][0] for r in result if r['opcode'] == 2 and r['register'] == 5]
    assert ids and ctls and 13 in cmds
    return dict(sync_offset=sync, idcodes=[hex(x) for x in ids],
                ctl_writes=[hex(x) for x in ctls],
                ctl_dec_bit_ever_set=any(x & 0x40 for x in ctls),
                mfwr_register_writes=sum(r['opcode'] == 2 and r['register'] == 27 for r in result),
                mfw_commands=cmds.count(2), desync_seen=13 in cmds,
                all_bytes_accounted_for=True, packet_count=len(result),
                fdri_words=sum(r['word_count'] for r in result if r['opcode'] == 2 and r['register'] == 3),
                packets=result)


def analyze(p, out):
    d = p.read_bytes()
    assert d[:5] == b'\x7fELF\x01' and d[5] == 1
    h = struct.unpack_from('<16sHHIIIIIHHHHHH', d)
    assert h[2] == 40
    sections = [struct.unpack_from('<IIIIIIIIII', d, h[6] + i * h[11]) for i in range(h[12])]
    sstr = sections[h[13]]
    section_names = d[sstr[4]:sstr[4] + sstr[5]]
    rows = []
    for table in sections:
        if table[1] != 2:
            continue
        st = sections[table[6]]
        names = d[st[4]:st[4] + st[5]]
        for off in range(table[4], table[4] + table[5], table[9]):
            n, v, size, info, _, idx = struct.unpack_from('<IIIBBH', d, off)
            name = names[n:names.find(b'\0', n)].decode()
            if 'fpga_code' not in name:
                continue
            assert info & 15 == 1
            sec = sections[idx]
            assert sec[1] != 8 and sec[3] <= v and v + size <= sec[3] + sec[5]
            fileoff = sec[4] + v - sec[3]
            blob = d[fileoff:fileoff + size]
            raw = gzip.decompress(blob)  # verifies gzip CRC32 and ISIZE
            assert blob[:4] == bytes.fromhex('1f8b0808')
            filename = blob[10:blob.index(b'\0', 10)].decode('ascii')
            assert Path(filename).name == filename
            dest = out / p.stem
            dest.mkdir(parents=True, exist_ok=True)
            (dest / (filename + '.gz')).write_bytes(blob)
            (dest / filename).write_bytes(raw)
            parsed = packets(raw)
            (dest / (filename + '.packets.json')).write_text(json.dumps(parsed, indent=2) + '\n')
            secname = section_names[sec[0]:section_names.find(b'\0', sec[0])].decode()
            rows.append(dict(mangled=name, demangled=name.split('fpga_code')[0].replace('_ZL14', '').replace('_ZL13', '') + 'fpga_code',
                             address=hex(v), size=size, section=secname, file_offset=hex(fileoff),
                             gzip_sha256=sha(blob), raw_filename=filename, raw_size=len(raw), raw_sha256=sha(raw),
                             gzip_crc32_isize_verified=True,
                             **{k: val for k, val in parsed.items() if k != 'packets'}))
    return dict(input=str(p), elf_sha256=sha(d), elf_size=len(d), images=rows,
                scope='STT_OBJECT symbols whose original name contains fpga_code; not an exhaustive firmware scan')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, action='append', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    report = dict(platform=platform.platform(), python=platform.python_version(),
                  script_sha256=sha(Path(__file__).read_bytes()),
                  crc_scope='gzip CRC verified; FPGA configuration CRC recorded but not recomputed',
                  inputs=[analyze(p, args.out) for p in args.input])
    (args.out / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    for item in report['inputs']:
        print(item['input'], item['elf_sha256'], 'images', len(item['images']))
        for row in item['images']:
            print(row['raw_filename'], row['raw_size'], row['idcodes'], 'DEC', row['ctl_dec_bit_ever_set'],
                  'MFWR', row['mfwr_register_writes'], 'MFW', row['mfw_commands'],
                  'packets', row['packet_count'], 'FDRI words', row['fdri_words'])
