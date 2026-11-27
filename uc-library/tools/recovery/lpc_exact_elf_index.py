"""Process-local verified ELF snapshots; no original-symbol/range check is elided."""
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from threading import RLock
from types import MappingProxyType
from elftools.elf.elffile import ELFFile


def fingerprint(path):
    stat = path.stat()
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


@dataclass(frozen=True)
class VerifiedElf:
    path: Path
    expected_sha256: str
    provenance: tuple
    data: bytes
    symbols: dict
    sections: tuple


class ExactElfIndex:
    def __init__(self):
        self._entries = {}
        self._lock = RLock()
        self.snapshots_built = 0
        self.range_checks = 0

    def _snapshot(self, input_path, expected_sha256):
        path = Path(input_path).resolve(strict=True)
        before = fingerprint(path)
        key = (path, expected_sha256, before)
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                with path.open('rb') as stream:
                    data = stream.read()
                assert fingerprint(path) == before, 'ELF changed during snapshot read'
                assert sha256(data).hexdigest() == expected_sha256, 'ELF SHA-256 mismatch'
                elf = ELFFile(BytesIO(data))
                symbols = {}
                for row in elf.get_section_by_name('.symtab').iter_symbols():
                    symbols.setdefault(row.name, []).append((row['st_shndx'], row['st_value'], row['st_size']))
                sections = tuple((section.name, section['sh_type'], section['sh_addr'], section['sh_offset'], section['sh_size']) for section in elf.iter_sections())
                assert fingerprint(path) == before, 'ELF changed during index creation'
                entry = VerifiedElf(path, expected_sha256, before, data,
                                    MappingProxyType({name: tuple(rows) for name, rows in symbols.items()}), sections)
                # Drop superseded provenance only for this physical path/hash.
                self._entries = {k: v for k, v in self._entries.items() if k[:2] != key[:2]}
                self._entries[key] = entry
                self.snapshots_built += 1
            assert fingerprint(path) == entry.provenance, 'ELF changed before range check'
            return entry

    def verify(self, root, original):
        input_path = Path(root) / original['elf_path']
        entry = self._snapshot(input_path, original['elf'])
        matching = [row for row in entry.symbols.get(original['mangled'], ())
                    if row == (original['section'], original['address'], original['size'])]
        row, = matching
        name, kind, address, file_offset, size = entry.sections[row[0]]
        assert name == original['section_name'] and kind == 'SHT_PROGBITS'
        offset = file_offset + (original['address'] & ~1) - address
        assert offset == original['file_offset'] and file_offset <= offset
        assert offset + original['size'] <= file_offset + size
        data = entry.data[offset:offset + original['size']]
        assert data.hex() == original['range_hex']
        assert sha256(data).hexdigest() == original['range_sha256']
        assert input_path.resolve(strict=True) == entry.path, 'ELF input path changed during range check'
        assert fingerprint(entry.path) == entry.provenance, 'ELF changed during range check'
        with self._lock:
            self.range_checks += 1
