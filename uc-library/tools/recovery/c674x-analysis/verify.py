"""Independent section/range replay and closed-artifact mirror audit."""
import argparse
import hashlib
import json
import platform
import struct
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--evidence', type=Path, required=True)
    ap.add_argument('--input', type=Path)
    ap.add_argument('--check-mirror', action='store_true')
    args = ap.parse_args()
    root = args.evidence
    if args.check_mirror:
        rows = json.loads((root / 'artifact-hashes.json').read_text())
        for name, digest in rows.items():
            assert sha((root / name).read_bytes()) == digest, name
        print('Mirror verified:', len(rows), 'files')
        return
    assert platform.system() == 'Linux', 'canonical replay must be Linux'
    raw = args.input.read_bytes()
    extract = root / 'extraction-01'
    manifest = json.loads((extract / 'manifest.json').read_text())
    assert sha(raw) == manifest['elf_sha256']
    header = struct.unpack_from('<16sHHIIIIIHHHHHH', raw)
    sections = [struct.unpack_from('<IIIIIIIIII', raw, header[6] + i * header[11])
                for i in range(header[12])]

    def replay(address, size, file_offset, expected):
        candidates = [s for s in sections if s[1] != 8 and s[2] & 2
                      and s[3] <= address and address + size <= s[3] + s[5]]
        assert len(candidates) == 1
        sec = candidates[0]
        actual = sec[4] + address - sec[3]
        assert actual == file_offset
        data = raw[actual:actual + size]
        assert sha(data) == expected
        return data

    synthetic = (extract / 'dsp-load-image.synthetic.elf').read_bytes()
    eh = struct.unpack_from('<16sHHIIIIIHHHHHH', synthetic)
    assert eh[2] == 140 and eh[4] == 0x80000000 and eh[10] == 10
    for index, row in enumerate(manifest['segments']):
        data = replay(int(row['source_va'], 16), row['size'], int(row['source_file_offset'], 16), row['sha256'])
        assert (extract / row['filename']).read_bytes() == data
        ph = struct.unpack_from('<IIIIIIII', synthetic, eh[5] + index * eh[9])
        assert ph[0] == 1 and ph[2] == int(row['destination_va'], 16) and ph[4] == row['size']
        assert synthetic[ph[1]:ph[1] + ph[4]] == data
    host = json.loads((root / 'host-trace-01/manifest.json').read_text())
    assert host['elf_sha256'] == manifest['elf_sha256']
    for row in host['functions']:
        replay(int(row['address'], 16), row['size'], int(row['file_offset'], 16), row['sha256'])
    process = json.loads((extract / 'process-map.json').read_text())
    trace = json.loads((extract / 'dsp-trace.json').read_text())
    for name, digest in process['inputs'].items():
        assert sha((extract / name).read_bytes()) == digest
    for row in process['mapped_processes']:
        assert sha((extract / row['callback_window']['file']).read_bytes()) == row['callback_window']['sha256']
    assert len(process['mapped_processes']) == 7 and len(process['discovered_tables']) == 29
    assert trace['cinit']['fully_accounted'] and len(trace['cinit']['records']) == 64
    proof = dict(platform=platform.platform(), source_elf_sha256=sha(raw),
                 extracted_ranges_replayed=len(manifest['segments']),
                 synthetic_segments_replayed=eh[10], host_function_ranges_replayed=len(host['functions']),
                 process_bindings=7, tables=29, cinit_records=64,
                 script_sha256=sha(Path(__file__).read_bytes()),
                 status='passed; static byte/identity audit, not hardware or algorithm-equivalence testing')
    (root / 'verification.json').write_text(json.dumps(proof, indent=2) + '\n')
    hashes = {}
    for file in sorted(root.rglob('*')):
        assert not file.is_symlink()
        if file.is_file() and file.name != 'artifact-hashes.json':
            hashes[file.relative_to(root).as_posix()] = sha(file.read_bytes())
    (root / 'artifact-hashes.json').write_text(json.dumps(hashes, indent=2) + '\n')
    print(json.dumps(proof))
    print('Artifact files sealed:', len(hashes))


if __name__ == '__main__':
    main()
