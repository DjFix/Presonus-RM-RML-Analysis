"""Compare a host replay with independently observed, hash-bound ARM fixtures."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from elftools.elf.elffile import ELFFile

TASK = Path(__file__).parent.name
DOMAINS = {
    's03': ('activation', 'Signed integer mode transitions including distinct modes, equal modes and non-binary dirty words in both roles.'),
    's15': ('element-constructor', 'Both original Element constructor variants in both roles with zero, signed mixed values and int32 boundaries.'),
    's16': ('offscreen-constructor', 'Both original Offscreen constructor variants in both roles delegating to Element C2 with zero, signed mixed values and int32 boundaries.'),
    's17': ('offscreen-destruction', 'Both roles: ordinary Offscreen teardown preserves receiver storage; deleting teardown releases that exact receiver via unsized delete.'),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(argv, **kwargs):
    return subprocess.run(argv, check=True, text=True, capture_output=True, **kwargs).stdout


def function_relocations(path, name):
    with path.open('rb') as source:
        elf = ELFFile(source)
        symbols = elf.get_section_by_name('.symtab')
        symbol, = symbols.get_symbol_by_name(name)
        section = symbol['st_shndx']
        offset = symbol['st_value']
        size = symbol['st_size']
        assert symbol['st_info']['type'] == 'STT_FUNC' and size > 0
        names = set()
        for relocations in elf.iter_sections():
            if relocations['sh_type'] not in ('SHT_REL', 'SHT_RELA') or relocations['sh_info'] != section:
                continue
            table = elf.get_section(relocations['sh_link'])
            for relocation in relocations.iter_relocations():
                if offset <= relocation['r_offset'] < offset + size:
                    names.add(table.get_symbol(relocation['r_info_sym']).name)
    return names


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--object', type=Path, required=True)
    parser.add_argument('--fixtures', type=Path, required=True)
    parser.add_argument('--integration', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    mode, domain = DOMAINS[TASK[-3:]]
    rows = json.loads(args.fixtures.read_text())['originals']
    names = {line.split()[-1] for line in run(['nm', '--defined-only', str(args.object)]).splitlines() if line.split()}
    missing = sorted({row['mangled'] for row in rows} - names)
    assert not missing, missing
    if mode == 'offscreen-destruction':
        delete = '_ZN8Presonus5Panel16OffscreenElementdlEPv'
        unsized = '_ZdlPv'
        sized = '_ZdlPvm'
        d0 = next(row['mangled'] for row in rows if 'D0Ev' in row['mangled'])
        d0_calls = function_relocations(args.object, d0)
        assert sized not in d0_calls
        if unsized not in d0_calls:
            assert delete in d0_calls
            wrapper_calls = function_relocations(args.object, delete)
            assert unsized in wrapper_calls and sized not in wrapper_calls
    inputs, expected = [], []
    for row in rows:
        for case in row['cases']:
            values = case['input']
            if mode == 'offscreen-destruction':
                values = [0 if 'D0Ev' in row['mangled'] else 1]
            inputs.append(' '.join(map(str, values)))
            expected.append(case['expected'])
    actual = run([str(args.exe.resolve()), mode], input='\n'.join(inputs) + '\n').splitlines()
    assert actual == expected, (actual, expected)
    classes = ['Element'] if TASK[-3:] in ('s03', 's15') else ['Element', 'OffscreenElement']
    paths = [f'{directory}/{name}.{ext}' for name in classes for directory, ext in (
        ('include/presonus/panel', 'hpp'), ('src/Presonus/Panel', 'cpp'))]
    sources = {path: digest(Path('uc-library') / path) for path in paths}
    pending = TASK.endswith('s03')
    proposed = []
    for row in rows:
        result = {key: row[key] for key in ('mangled', 'firmware', 'role', 'address', 'size', 'section')}
        result.update(original_elf_sha256=row['elf_sha256'], cpp_compiled=True,
                      mangling_namespace_checked=True, portable_ready=not pending,
                      domain=domain, sources=sources)
        if pending:
            result['declaration_uncertainties'] = ['The original non-template return declaration is unencoded; portable source exposes void.']
        proposed.append(result)
    receipt = {
        'passed': True,
        'domain': domain,
        'case_count': len(expected),
        'originals': rows,
        'fixtures_sha256': digest(args.fixtures),
        'object_sha256': digest(args.object),
        'executable_sha256': digest(args.exe),
        'integration_sha256': digest(args.integration) if args.integration.is_file() else None,
        'proposed_readiness': {'ready': [] if pending else proposed, 'pending': proposed if pending else []},
    }
    args.out.write_text(json.dumps(receipt, indent=2) + '\n')
    print(f'{len(expected)} matching portable cases across {len(rows)} exact original ranges')


if __name__ == '__main__':
    main()
