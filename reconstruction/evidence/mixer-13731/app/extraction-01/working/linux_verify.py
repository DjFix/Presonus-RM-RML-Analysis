"""Nonexecuting Linux byte verification and bounded Thumb/ARM startup decoding."""
import hashlib
import json
from pathlib import Path
import platform
import struct
import sys
import capstone

out = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(out))
from extract import elf_objects


def sha(b):
    return hashlib.sha256(b).hexdigest()


manifest = json.loads((out/'manifest.json').read_text())
results = []
prefixes = []
for rec in manifest:
    for o in rec['objects']:
        b = (out/o['output']).read_bytes()
        assert sha(b) == o['sha256'] and len(b) == o['size']
for rec, name in zip(manifest[:2], ('mixer-13731.elf', 'surface-13840.elf')):
    elf = (out/'inputs'/name).read_bytes()
    assert sha(elf) == rec['input_elf_sha256']
    original = {meta['symbol']: (meta, b) for meta, b in elf_objects(elf)}
    for o in rec['objects']:
        meta, b = original[o['symbol']]
        assert b == (out/o['output']).read_bytes()
        assert meta['file_offset'] == o['file_offset']
        if 'arm_code' not in o['symbol'] and 'dice3_surface' not in o['symbol']:
            continue
        if 'arm_code' in o['symbol']:
            base = 0x08000000
            pc = struct.unpack_from('<I', b, 4)[0] & ~1
            mode = capstone.CS_MODE_THUMB
            offset = pc-base
        else:
            base = struct.unpack_from('<I', b, 8)[0]-16
            offset = 16
            pc = base+offset
            mode = capstone.CS_MODE_ARM
        md = capstone.Cs(capstone.CS_ARCH_ARM, mode | capstone.CS_MODE_LITTLE_ENDIAN)
        decoded = list(md.disasm(b[offset:offset+96], pc))
        assert len(decoded) >= 6
        results.append(dict(symbol=o['symbol'], source_elf_sha256=sha(elf),
                            image_sha256=sha(b), mode='Thumb' if mode == capstone.CS_MODE_THUMB else 'ARM',
                            entry=hex(pc), file_offset=hex(offset), instructions=len(decoded),
                            scope='bounded startup disassembly; not execution or semantic validation'))
        prefixes.append('\n# '+o['symbol'])
        prefixes.extend(f'{i.address:08x} {i.bytes.hex():8} {i.mnemonic} {i.op_str}' for i in decoded)
proof = dict(platform=platform.platform(), python=sys.version, capstone=capstone.__version__,
             manifest_sha256=sha((out/'manifest.json').read_bytes()),
             verified_export_instances=sum(len(r['objects']) for r in manifest),
             original_elf_replay_instances=sum(len(r['objects']) for r in manifest[:2]),
             original_elfs_replayed=2, startup_decodes=results,
             firmware_executed=False, hardware_validated=False,
             reconstructed_functions=0)
(out/'linux-verification.json').write_text(json.dumps(proof, indent=2)+'\n')
(out/'startup-disassembly.txt').write_text('\n'.join(prefixes)+'\n')
print(json.dumps(proof, indent=2))
