"""Independently cross-check exact postadmission rows and once-only slot credit."""
import collections
import hashlib
import json
from pathlib import Path
import sys

def read(path):
    return json.loads(Path(path).read_bytes())

def checked(record):
    path = Path(record["path"])
    assert hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"], path
    return read(path)

ledger = read(sys.argv[1])
targets = ledger["targets"]
expected = collections.defaultdict(set)
owner = {}
for proof in ledger["selected_proposals"]:
    for lane in checked(proof)["lanes"]:
        for task in lane["candidates"]:
            original = task["target"]
            exact = {(original["elf_sha256"], original["original_mangled"])}
            exact |= {(row["elf"], row["mangled"]) for row in task["covered_originals"]}
            name = task["task_id_override"]
            for key in exact:
                assert owner.setdefault(key, name) == name
            expected[name].update(exact)

admitted = {}
for batch in targets["admission_batches"]:
    verification = checked(batch["verification"])
    for row in checked(verification["artifacts"]["NOTES.json"])["rows"]:
        key = tuple(row["identity"])
        assert key not in admitted, key
        admitted[key] = row["task"]
confirmed = collections.defaultdict(list)
mapping = targets["replacement_to_primary_slot"]
for name, keys in expected.items():
    if all(admitted.get(key) == name for key in keys):
        confirmed[mapping.get(name, name)].append(name)
retained_or_helper = {key:task for key,task in admitted.items() if task not in expected}
actual = {
    "fully_admitted_primary_slots": len(confirmed),
    "fully_admitted_exact_elf_identities": len(admitted),
    "cross_counted_slots": [key for key, names in confirmed.items() if len(names) > 1],
    "retained_or_helper_elf": [{"identity": key, "task": task} for key,task in sorted(retained_or_helper.items())],
    "accepted_replacements": sorted(name for names in confirmed.values() for name in names if name in mapping),
}
assert len(confirmed) == targets["fully_admitted_primary_slots"]
assert len(admitted) == targets["verified_admitted_distinct_elf_identities"]
assert sorted(actual["cross_counted_slots"]) == targets["primary_slots_with_multiple_fully_admitted_actual_assignments"]
assert actual["accepted_replacements"] == targets["fully_admitted_replacements"]
assert sorted(retained_or_helper) == sorted(map(tuple, targets["retained_elf_identities_verified_admitted"]))
print(json.dumps(actual, indent=2))
