"""Offline ELF32 payload extraction; no hardware operations or third-party modules."""
import hashlib
import json
from pathlib import Path
import re
import struct
import tarfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def sha(b):
    return hashlib.sha256(b).hexdigest()


def elf_objects(b):
    assert b[:6] == b'\x7fELF\x01\x01', 'requires little-endian ELF32'
    h = struct.unpack_from('<16sHHIIIIIHHHHHH', b)
    assert h[2] == 40, 'requires ARM ELF'
    sections = [struct.unpack_from('<IIIIIIIIII', b, h[6] + i*h[11])
                for i in range(h[12])]
    if not sections:
        return
    ns = sections[h[13]]
    names = b[ns[4]:ns[4]+ns[5]]

    def string(data, off):
        end = data.index(b'\0', off)
        return data[off:end].decode('utf-8', 'replace')

    for s in sections:
        if s[1] != 2:
            continue
        st = sections[s[6]]
        strings = b[st[4]:st[4]+st[5]]
        for off in range(s[4], s[4]+s[5], s[9]):
            n, v, size, info, other, idx = struct.unpack_from('<IIIBBH', b, off)
            name = string(strings, n)
            if (info & 15) != 1 or not re.fullmatch(
                    r'(?:_ZL[0-9]+(?:noaa|nimh|esa)_(?:arm|fpga)_code|'
                    r'_ZL9fpga_code|_ZL18dice3_surface_code|'
                    r'xrackpanel_code|xmenpanel_code|panel_surface_code|fwupdateScript_code)', name) or not size:
                continue
            if idx >= len(sections):
                continue
            sec = sections[idx]
            if sec[1] == 8:
                continue
            delta = v-sec[3]
            assert 0 <= delta and delta+size <= sec[5], name
            start = sec[4]+delta
            payload = b[start:start+size]
            assert len(payload) == size
            segments = [struct.unpack_from('<IIIIIIII', b, h[5]+i*h[9])
                        for i in range(h[10])]
            segment_matches = [p for p in segments if p[0] == 1 and
                               p[2] <= v and v+size <= p[2]+p[4] and
                               p[1]+v-p[2] == start]
            assert segment_matches, f'PT_LOAD does not corroborate section mapping: {name}'
            yield dict(symbol=name, address=hex(v), size=size,
                       section=string(names, sec[0]), file_offset=hex(start),
                       pt_load_mapping_verified=True, sha256=sha(payload)), payload


def inspect(p):
    words = list(struct.unpack_from('<16I', p)) if len(p) >= 64 else []
    vectors = []
    for off in range(0, min(len(p)-64, 4096)+1, 4):
        w = struct.unpack_from('<16I', p, off)
        if not (0x20000000 <= w[0] <= 0x20080000 and w[0] % 4 == 0):
            continue
        if not (0x08000001 <= w[1] < 0x08200000 and w[1] & 1):
            continue
        if any(w[i] != 0 for i in (7, 8, 9, 10, 13)):
            continue
        vectors.append(dict(offset=hex(off), words=[hex(x) for x in w]))
    strings = [m.group().decode('ascii') for m in re.finditer(rb'[\x20-\x7e]{8,}', p)]
    interesting = [s for s in strings if re.search(
        r'stm|xmen|shelby|panel|firmware|version|copyright|dice|built|gcc|keil|iar', s, re.I)]
    header = None
    if len(p) >= 8:
        sp, pc = struct.unpack_from('<II', p)
        if 0x20000000 <= sp <= 0x20010000 and 0x08000001 <= pc < 0x08080000 and pc & 1:
            header = dict(candidate_base='0x08000000', initial_sp=hex(sp),
                          reset_pointer=hex(pc), reset_file_offset=hex((pc & ~1)-0x08000000),
                          caveat='First two words are consistent with STM32; following words are not a conventional complete vector table. Preserve whole image.')
    return dict(first_16_words=[hex(x) for x in words], stm32_header=header,
                stm32_vector_candidates=vectors, interesting_strings=interesting)


def main():
    records = []
    inputs = [(str(p.relative_to(ROOT)), None, p.read_bytes())
              for p in (ROOT/'Cutter Analysis/mixer', ROOT/'Cutter Analysis/surface')]
    for p in sorted((ROOT/'firmware').glob('*/upgrade.bin')):
        with tarfile.open(p) as t:
            for m in t.getmembers():
                if m.isfile() and m.name in ('files/mixer', 'files/surface'):
                    inputs.append((str(p.relative_to(ROOT)), m.name, t.extractfile(m).read()))
    for source, member, b in inputs:
        if b[:4] != b'\x7fELF':
            raise ValueError(f'non-ELF input: {source}:{member}')
        label = Path(source).parent.name if member else Path(source).name+'-analysis'
        dest = OUT/'images'/label
        dest.mkdir(parents=True, exist_ok=True)
        rec = dict(source=source, archive_member=member, input_elf_sha256=sha(b),
                   input_elf_size=len(b), objects=[])
        rec['section_table_present'] = bool(struct.unpack_from('<H', b, 48)[0])
        for meta, payload in elf_objects(b):
            path = dest/(meta['symbol']+'.bin')
            path.write_bytes(payload)
            assert path.read_bytes() == b[int(meta['file_offset'],16):int(meta['file_offset'],16)+meta['size']]
            meta.update(output=str(path.relative_to(ROOT)), verified_source_bytes=True,
                        analysis=inspect(payload))
            rec['objects'].append(meta)
        records.append(rec)
        print(label, 'ELF', sha(b)[:12], 'section_table', rec['section_table_present'], [(x['symbol'], x['size'], len(x['analysis']['stm32_vector_candidates'])) for x in rec['objects']])
    (OUT/'manifest.json').write_text(json.dumps(records, indent=2)+'\n')


if __name__ == '__main__':
    main()
