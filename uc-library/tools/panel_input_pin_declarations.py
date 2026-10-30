#!/usr/bin/env python3
"""Targeted declaration/caller evidence; do not turn unused R0 into void proof."""
import hashlib
import json
from pathlib import Path
import sys
from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM
from elftools.elf.elffile import ELFFile


def sha(data):
    return hashlib.sha256(data).hexdigest()


root = Path(sys.argv[1]).resolve()
out = root / 'uc-library/validation/panel-input-pin/return-declarations.json'
records = {}
for role in ('client', 'server'):
    directory = root / 'uc-library/recovered-all' / role
    manifest = json.loads((directory / 'manifest.json').read_text())
    path = root / manifest['path']
    raw = path.read_bytes()
    assert sha(raw) == manifest['sha256']
    rows = json.loads((directory / 'symbols.json').read_text())
    target = next(s for s in rows if s['mangled'] == '_ZN8Presonus5Panel8InputPin5setupEiPNS0_16PinStateObserverE')
    units, matches = [], []
    with path.open('rb') as stream:
        elf = ELFFile(stream)
        debug = {s.name: dict(bytes=s['sh_size'], sha256=sha(s.data())) for s in elf.iter_sections() if s.name.startswith('.debug')}
        for cu in elf.get_dwarf_info().iter_CUs():
            value = cu.get_top_DIE().attributes.get('DW_AT_name')
            units.append(value.value.decode(errors='replace') if value else '')
            for die in cu.iter_DIEs():
                for key in ('DW_AT_name', 'DW_AT_linkage_name', 'DW_AT_MIPS_linkage_name'):
                    value = die.attributes.get(key)
                    if value and isinstance(value.value, bytes) and any(name in value.value for name in (b'LEDControl', b'InputPin', b'Presonus')):
                        matches.append(dict(offset=die.offset, tag=die.tag, attribute=key, value=value.value.decode(errors='replace')))
        cs = Cs(CS_ARCH_ARM, CS_MODE_ARM)
        callers = []
        for variant in ('C1', 'C2'):
            name = '_ZN8Presonus5Panel8InputPin' + variant + 'EiPNS0_16PinStateObserverE'
            s = next(s for s in rows if s['mangled'] == name)
            section = elf.get_section(s['section'])
            offset = int(section['sh_offset']) + s['address'] - int(section['sh_addr'])
            data = (directory / s['export_path']).read_bytes()
            assert offset == s['file_offset'] and data == raw[offset:offset + s['size']]
            instructions = list(cs.disasm(data, s['address']))
            for index, ins in enumerate(instructions):
                if ins.mnemonic == 'bl' and ins.op_str == hex(target['address']).replace('0x', '#0x'):
                    after = instructions[index + 1:index + 5]
                    overwritten = bool(after and after[0].mnemonic == 'mov' and after[0].op_str.startswith('r0, r'))
                    callers.append(dict(caller=s, call_address=ins.address, post_call=[dict(address=i.address, mnemonic=i.mnemonic, operands=i.op_str) for i in after],
                                        result_immediately_overwritten=overwritten, proves_return_declaration=False))
    assert not matches and len(callers) == 2
    records[role] = dict(original_elf_sha256=manifest['sha256'], debug_sections=debug, compilation_units=units,
                         targeted_presonus_led_input_die_matches=matches, setup_constructor_callers=callers,
                         conclusion='Runtime-only DWARF does not declare these app methods. Constructor call sites overwrite setup R0; no original return declaration is proven.')
report = dict(kind='Targeted app return-declaration evidence', records=records,
              original_return_declarations_verified=False,
              setup_status_r0_observation='Original setup instruction paths explicitly produce0/-1; that observable machine status is tested separately, without claiming historical C++ spelling.',
              led_status='No LED declaration DIE found; ignored callback-dependent R0 remains insufficient to prove void.', tool_sha256=sha(Path(__file__).read_bytes()))
out.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(dict(output=str(out), sha256=sha(out.read_bytes()), declarations_verified=False), indent=2))
