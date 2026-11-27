"""Read back all three authorized dispatches against their exact task and ELF scope."""
import json
from pathlib import Path

from packet_cycle import CYCLE, ROOT, read, reference
from context_runtime import sha

P = CYCLE / "packeting"
AUTH = P / "ACTUAL08-VERIFIED-PROPOSED10-AUTHORITY-REVIEW01.json"
AUTH_SHA = "ba97032f10922d954ea8699ed913322b85fe5c9c017640a06068317491de5231"


def key(target):
    return tuple(target[field] for field in ("original_elf_sha256", "mangled", "address", "size", "section"))


def main():
    assert sha(AUTH) == AUTH_SHA
    authority = read(AUTH)
    expected_generation = authority["active"]["state_sha256"]
    batches = []
    originals = set()
    for wave_number, reviewed in enumerate(authority["waves"], 1):
        directory = P / f"actual08-authorized-wave{wave_number:02}-capture01"
        dispatch_path, snapshot_path = directory / "BATCH_DISPATCH.json", directory / "SNAPSHOT.json"
        dispatch, snapshot = read(dispatch_path), read(snapshot_path)
        assert dispatch["generation"] == expected_generation == snapshot["active"]["state_sha256"]
        assert dispatch["publication_state"] == "complete" and dispatch["dependency_conflicts"] == []
        assert AUTH_SHA in dispatch["production_continuation"] and AUTH_SHA in dispatch["smaller_batch_authorization"]
        expected_owners = {owner: [row["task"] for row in rows] for owner,rows in reviewed["owners"].items()}
        assert {worker["arguments"]["task_name"]: [Path(path).name for path in worker["packets"]]
                for worker in dispatch["workers"]} == expected_owners
        tasks = {row["task"]: row for rows in reviewed["owners"].values() for row in rows}
        assert set(tasks) == {Path(packet).name for packet in dispatch["packet_manifests"]}
        reviewed_inventory = read(ROOT / reviewed["native_inventory"]["path"])
        assert sha(ROOT / reviewed["native_inventory"]["path"]) == reviewed["native_inventory"]["sha256"]
        kit = {row["task_id"]: row for lane in reviewed_inventory["lanes"] for row in lane["tasks"]}
        sealed = {}
        for packet, expected_seal in dispatch["packet_manifests"].items():
            packet = ROOT / packet
            assert packet.parent.parent == directory and sha(packet / "context.json") == expected_seal
            request = read(packet / "request.json")
            item = tasks[packet.name]
            assert request["task_id"] == item["task"]
            assert request["targets"] == item["originals"]
            assert request["work_binding"]["work_item_id"] == item["work_item_id"]
            assert sorted(kit[packet.name]["production"]) == sorted(item["owned_files"])
            assert sorted(request["owned_files"]) == sorted(kit[packet.name]["owned"])
            for target in request["targets"]:
                assert key(target) not in originals
                originals.add(key(target))
            sealed[packet.name] = dict(context_sha256=expected_seal, work_item_id=item["work_item_id"],
                                       originals=request["targets"], owned_files=request["owned_files"])
        batches.append(dict(wave=wave_number, owners=expected_owners, tasks=sealed,
                            dispatch=reference(dispatch_path,"review_record","Complete validated exact batch publication"),
                            snapshot=reference(snapshot_path,"review_record","Verified compact exact capture"),
                            physical_copy_bytes=snapshot["physical_copy_bytes"]))
    assert [len(batch["tasks"]) for batch in batches] == [7, 2, 1]
    assert len(originals) == 18
    output = P / "ACTUAL08-FINAL10-DISPATCH-READBACK01.json"
    with output.open("x") as handle:
        json.dump(dict(authority_sha256=AUTH_SHA, generation=expected_generation, total_tasks=10, total_originals=18,
                       batches=batches), handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(output, sha(output))


if __name__ == "__main__":
    main()
