#!/usr/bin/env python3
"""Probe application declaration metadata; never decode or recover Core bodies."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from elftools.elf.elffile import ELFFile


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def value(attribute):
    item = attribute.value
    if isinstance(item, bytes):
        return item.decode('utf-8', errors='backslashreplace')
    return item


def describe(die):
    return dict(offset=die.offset, tag=die.tag,
                attributes={key: dict(form=attr.form, value=value(attr))
                            for key, attr in die.attributes.items()})


def type_chain(die):
    output, seen = [], set()
    while 'DW_AT_type' in die.attributes:
        die = die.get_DIE_from_attribute('DW_AT_type')
        if die is None or die.offset in seen:
            break
        seen.add(die.offset)
        output.append(describe(die))
        if len(output) >= 24:
            break
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repository', type=Path)
    parser.add_argument('--name', action='append', required=True)
    args = parser.parse_args()
    for name in args.name:
        if not name or name.startswith('Core'):
            raise SystemExit('select explicit application declaration names')
    repo = args.repository.resolve()
    library = repo / 'uc-library'
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    output = repo / 'evidence/recovery/2026-10-27/application-dwarf' / stamp
    output.mkdir(parents=True, exist_ok=False)
    reports = {}
    for role in ('client', 'server'):
        manifest = json.loads((library / 'recovered-all' / role / 'manifest.json').read_text())
        source = (repo / manifest['path']).resolve(strict=True)
        assert source.is_relative_to(repo) and sha(source) == manifest['sha256']
        units, matches, entries = [], [], 0
        with source.open('rb') as stream:
            elf = ELFFile(stream)
            sections = {section.name: section['sh_size'] for section in elf.iter_sections()
                        if section.name.startswith(('.debug_', '.zdebug_'))}
            if elf.has_dwarf_info():
                dwarf = elf.get_dwarf_info()
                for unit in dwarf.iter_CUs():
                    top = unit.get_top_DIE()
                    units.append(describe(top))
                    for die in unit.iter_DIEs():
                        entries += 1
                        names = [value(attribute) for key, attribute in die.attributes.items()
                                 if key in ('DW_AT_name', 'DW_AT_linkage_name', 'DW_AT_MIPS_linkage_name')]
                        if any(needle in name for needle in args.name
                               for name in names if isinstance(name, str)):
                            record = describe(die)
                            record['type_chain'] = type_chain(die)
                            record['children'] = [describe(child) for child in die.iter_children()]
                            matches.append(record)
        reports[role] = dict(source=manifest['path'], elf_sha256=manifest['sha256'],
                             debug_sections=sections, compile_units=units,
                             dies_examined=entries, matching_declarations=matches,
                             matching_declaration_count=len(matches))
    report = dict(requested_names=args.name, roles=reports,
                  core_bodies_decoded=False, original_code_executed=False,
                  tool_sha256=sha(Path(__file__)),
                  scope='Existing DWARF declaration metadata only. Absence applies to these names and supplied ELFs, not all possible external debug files.')
    path = output / 'validation.json'
    path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(proof=str(path.relative_to(repo)), sha256=sha(path),
                          matches={key: record['matching_declaration_count'] for key, record in reports.items()},
                          dies={key: record['dies_examined'] for key, record in reports.items()})))


if __name__ == '__main__':
    main()
