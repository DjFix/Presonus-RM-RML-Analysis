"""Execute exact LCDManager role thunks and the real RM Book provider chain."""
import argparse
import json
from pathlib import Path
import struct
import sys

from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "cycle20_g07_r21"))
from native import OriginalELF, ROLES, Trial, put_word, sha

MANGLED = "_ZNK8Presonus5Panel10LCDManager14getDefaultBookEv"
NATIVE_PROOF = Path("temp/recovery-work/control10x20-after-4fed70d11/"
                    "selection/ACTUAL07_LATE_LCD_MANAGER_NATIVE01.json")


def case_trial(row, code, providers, description):
    trial = Trial(row, code)
    manager, mixerlcd, first, second, roster = (0x41000000, 0x41010000, 0x41020000,
                                                0x41030000, 0x41040000)
    name = description["case"]
    match = name == "matching-tag"
    delegate = 0 if name == "null-delegate" else mixerlcd
    provider_entries = {}
    if providers:
        table_name = "_ZTVN8Presonus5Panel8MixerLCDE"
        thunk_name = "_ZThn212_NK8Presonus5Panel8MixerLCD14getDefaultBookEv"
        table, table_bytes = providers[table_name]
        thunk_entry = providers[thunk_name][0]["address"]
        assert struct.unpack_from("<I", table_bytes, 140)[0] == thunk_entry
        trial.put(table["address"], table_bytes)
        for symbol, (target, body) in providers.items():
            if symbol != table_name:
                provider_entries[target["address"]] = symbol
                trial.put(target["address"], body)
        if delegate:
            delegate += 212
            trial.put(delegate, put_word(table["address"] + 136))
        trial.put(mixerlcd + 0xe8, put_word(roster) + put_word(0 if name == "empty-roster" else 2))
        trial.put(roster, put_word(first) + put_word(second))
        trial.put(first + 0x8c, put_word(12))
        trial.put(second + 0x8c, put_word(11 if match else 13))
    elif delegate:
        table, callback = 0x43000000, 0x43001000
        trial.put(delegate, put_word(table))
        trial.put(table, put_word(0) + put_word(callback))
        trial.put(callback, bytes.fromhex("1eff2fe1"))
        provider_entries[callback] = "abstract-ILCDDelegate-second-slot"
    trial.put(manager + 4, put_word(delegate))

    trace = []
    def observe(emu, pc, _width, _context):
        if pc in provider_entries:
            symbol = provider_entries[pc]
            recv = emu.reg_read(UC_ARM_REG_R0)
            tag = emu.reg_read(UC_ARM_REG_R1)
            trace.append({"symbol": symbol, "receiver": recv, "arg_r1": tag})
            if symbol == "abstract-ILCDDelegate-second-slot":
                assert recv == delegate
                emu.reg_write(UC_ARM_REG_R0, second if match else 0)
    trial.uc.hook_add(UC_HOOK_CODE, observe)
    observed = trial.run(manager, 0)
    assert observed == description["result"]
    if not delegate:
        assert not trace
    elif providers:
        names = [row["symbol"] for row in trace]
        assert names[:3] == [
            "_ZThn212_NK8Presonus5Panel8MixerLCD14getDefaultBookEv",
            "_ZNK8Presonus5Panel8MixerLCD14getDefaultBookEv",
            "_ZNK8Presonus5Panel12LCDComponent7getBookEi"]
        assert [event["receiver"] for event in trace[:3]] == [delegate, mixerlcd, mixerlcd]
        assert trace[2]["arg_r1"] == 11
        expected_tags = [] if name == "empty-roster" else [first, second]
        assert [event["symbol"] for event in trace[3:]] == ["_ZNK8Presonus5Panel4Book6getTagEv"] * len(expected_tags)
        assert [event["receiver"] for event in trace[3:]] == expected_tags
    else:
        assert [event["symbol"] for event in trace] == ["abstract-ILCDDelegate-second-slot"]
    return description | {"exact_trace": trace}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    sealed = (args.snapshot / NATIVE_PROOF).read_bytes()
    assert sha(sealed) == "cfbbda960c86e5c457c542b9fa3c669028e6d4e4e9410f47844f5b3a5311a385"
    previous = {row["elf"]: row for row in json.loads(sealed)["cases"]}
    rows = []
    for digest, path, role, firmware, _ in ROLES:
        elf = OriginalELF(args.snapshot / path, digest)
        observed = previous[digest]
        row, code = elf.symbol(MANGLED)
        assert row["size"] == 48 and row["section"] == 12
        assert row["address"] == observed["exact_original_address"]
        assert row["range_sha256"] == observed["range_sha256"]
        providers = {}
        for name, approval in observed["native_provider_ranges"].items():
            detail, body = elf.symbol(name)
            assert detail["address"] == approval["address"] and detail["range_sha256"] == approval["sha256"]
            providers[name] = (detail, body)
        assert len(providers) == (5 if role == "server" else 0)
        rows.append(row | {"elf_sha256": digest, "role": role, "firmware": firmware,
            "provider_ranges": [detail for detail, _ in providers.values()],
            "cases": [case_trial(row, code, providers, case) for case in observed["cases"]]})
    args.out.write_text(json.dumps({"originals": rows, "review_sha256": sha(sealed)}, indent=2) + "\n")


if __name__ == "__main__":
    main()
