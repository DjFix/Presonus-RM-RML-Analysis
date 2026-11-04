"""Offline, repeatable LPC panel payload identification; never programs hardware."""
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import struct
import sys

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[2]
OUT = HERE if HERE.name == 'lpc-system-control' else ROOT / 'evidence/recovery/2026-10-27/lpc-system-control'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location('extract', Path(__file__).with_name('extract.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    records = []
    for role, original, expected, names in [
        ('surface', 'Cutter Analysis/surface', '304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0', ['panel_surface_code']),
        ('mixer', 'Cutter Analysis/mixer', '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07', ['xrackpanel_code', 'xmenpanel_code']),
    ]:
        saved = OUT / 'inputs' / (role + '.elf')
        if saved.exists():
            data = saved.read_bytes()
        else:
            data = (ROOT / original).read_bytes()
            saved.parent.mkdir(parents=True, exist_ok=True)
            saved.write_bytes(data)
        assert sha(data) == expected
        found = set()
        for meta, payload in mod.elf_objects(data):
            if meta['symbol'] not in names:
                continue
            found.add(meta['symbol'])
            vectors = struct.unpack_from('<48I', payload)
            assert vectors[0] == 0x10002000
            assert all(v == 0 or (v & 1 and 0 < (v & ~1) < len(payload)) for i, v in enumerate(vectors[:16]) if i not in (0, 7))
            assert len(payload) <= 65536
            regs = {}
            for name, address in [('SYSCON', 0x40048000), ('IOCON', 0x40044000), ('USART', 0x40008000)]:
                count = payload.count(struct.pack('<I', address))
                assert count > 0
                regs[name] = {'address': hex(address), 'literal_occurrences': count}
            dest = OUT / role / (meta['symbol'] + '.bin')
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                assert dest.read_bytes() == payload
            else:
                dest.write_bytes(payload)
            assert dest.read_bytes() == data[int(meta['file_offset'], 16):int(meta['file_offset'], 16) + meta['size']]
            meta.update(role=role, original_source=original, input_elf_sha256=expected,
                        output=str(dest.relative_to(OUT)), initial_sp=hex(vectors[0]),
                        reset_vector=hex(vectors[1]), analysis_base='0x0',
                        first_16_words=[hex(v) for v in vectors[:16]],
                        initial_vector_checksum=hex(sum(vectors[:8]) & 0xffffffff),
                        word_at_0x2fc=payload[0x2fc:0x300].hex(), peripheral_literals=regs,
                        identification='LPC-family Cortex-M panel update payload; LPC1317 consistent with supplied board identification',
                        exact_part_proven_from_binary=False, source_reconstructed=False,
                        hardware_validated=False, flash_ready=False)
            records.append(meta)
        assert found == set(names)
    result = {'platform': platform.platform(), 'python': sys.version, 'byte_extraction_verified': True,
              'section_and_PT_LOAD_mapping_verified': True, 'records': records,
              'scope': 'Static byte, vector and literal checks only; no execution or hardware validation.'}
    name = 'linux-verification.json' if platform.system() == 'Linux' else 'local-extraction.json'
    (OUT / name).write_text(json.dumps(result, indent=2) + '\n')
    for row in records:
        print(row['role'], row['symbol'], row['size'], row['sha256'], row['output'])
    print('PASS:', result['scope'])


if __name__ == '__main__':
    main()
