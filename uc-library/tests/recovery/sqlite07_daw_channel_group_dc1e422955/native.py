"""Replay original DAWChannelGroup calls with the original NumericParam bodies."""

import json
from pathlib import Path
import struct
import sys

from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2

ORACLE = Path(__file__).resolve().parents[1] / 'sqlite04_daw_045d71117e05' / 'native.py'
# The bound Machine lives in an earlier DAW provider replay.
import importlib.util

spec = importlib.util.spec_from_file_location('daw_original_machine', ORACLE)
provider = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = provider
spec.loader.exec_module(provider)

GET_CASES = [(-2.75, 3), (-0.75, 3), (0.75, 3), (2.75, 3), (3.0, 3),
             (8.25, 3), (1.5, 0), (-2.75, 0), (0.0, 0)]
RESET_CASES = [(0.0, 0), (-2.75, 0), (6.5, 3)]
SETTER = '_ZN4Core8Portable12NumericParam8setValueEfb'


def observe(original):
    provider.check_range(original)
    machine = provider.Machine(original)
    receiver, cached = provider.RECEIVER, provider.PARAMETERS
    mode = 'reset' if original['mangled'].endswith('resetUsedCountEv') else 'get'
    result = []
    for value, children in RESET_CASES if mode == 'reset' else GET_CASES:
        machine.construct('15DAWChannelGroup', receiver)
        machine.parameter(cached, 'used', 6, value)
        machine.uc.mem_write(cached + 0x200 + 40, struct.pack('<ff', -20, 20))
        machine.store(receiver + 0x84, cached)
        machine.children(receiver, [provider.CHILDREN + 0x100 * i for i in range(children)])
        setter = machine.load(machine.load(cached) + 0x58)
        assert setter == machine.address(SETTER)
        calls, writes = [], []

        def record_call(uc, address, width, _):
            calls.append([uc.reg_read(register)
                          for register in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2)])

        def record_write(uc, access, address, width, value, _):
            if receiver <= address < receiver + 0x88 or cached <= address < cached + 0x100:
                writes.append([address, width, value])

        hooks = [machine.uc.hook_add(UC_HOOK_CODE, record_call, begin=setter, end=setter),
                 machine.uc.hook_add(UC_HOOK_MEM_WRITE, record_write)]
        machine.events.clear()
        actual = machine.invoke(original['mangled'], receiver)
        for hook in hooks:
            machine.uc.hook_del(hook)
        final_value, = struct.unpack('<f', machine.uc.mem_read(cached + 0x2c, 4))
        assert machine.load(receiver + 0x84) == cached
        assert machine.load(receiver + 0x5c) == children
        if mode == 'reset':
            assert calls == [[cached, 0, 0]] and final_value == 0.0
            assert writes == ([[cached + 0x2c, 4, 0]] if value != 0.0 else [])
            expected = f'0 {len(writes)} 0'
        else:
            assert not calls and not writes and final_value == value
            assert machine.events[0] == [provider.GET_VALUE, cached]
            assert machine.events[1][0] == '__aeabi_f2iz'
            assert len(machine.events) == 2
            expected = str(provider.signed(actual))
        result.append(dict(value=value, children=children, final_value=final_value,
                           provider_trace=machine.events.copy(), setter_trace=calls,
                           writes=writes, expected=expected))
    return dict(original=original, mode=mode, cases=result)


def run(packet):
    context = json.loads(Path(packet).read_text())
    return [observe(entry['original']) for entry in context['originals']]


if __name__ == '__main__':
    print(json.dumps(run(sys.argv[1]), indent=2))
