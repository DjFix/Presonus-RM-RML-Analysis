"""Materialize one exact approved Actual07 wave using the currently bound evidence."""
from pathlib import Path
import sys

from packet_cycle import (
    CYCLE, ROOT, materialize, read, reference, rel, save, validate_request, verify_planned_equivalence,
)
from context_runtime import guard, inside, sha
from execution_review import batch_validation
from assemble_actual06_authorized import renewed_site
from reconstruction_contract import bound_files

P, S = CYCLE / "packeting", CYCLE / "selection"
AUTHORITY = P / "ACTUAL07-VERIFIED-PROPOSED67-AUTHORITY-REVIEW01.json"
AUTHORITY_SHA = "5619a57a148748e81d0b2b542b6e4dfe17930704e599ef92965b6daf55cd22a0"
GENERATION = "e82bb46c1ad32716918acda0b0cb8af4c8239982e64d09712fd70e0ef6e4a3c2"
COPY = CYCLE / "integration/preview-actual06-next42/ACCEPTED_PLAN.json"
REVIEW_FILES = (
    S / "ACTUAL05_FOLLOWON_G04_G09_REVIEW01.json",
    S / "POST_ACTUAL06_NEXT_READY09_REVIEW01.json",
    S / "ACTUAL07_G05_DRAFT_PART01_REVIEW01.json",
    S / "ACTUAL07_G05_DRAFT_PART02_REVIEW01.json",
    S / "ACTUAL07_BOOK_G07_SCANNERS_CURRENT_REVIEW01.json",
    S / "ACTUAL07_TYPED_G02_G03_MAX13_REVIEW_CANONICAL01.json",
    S / "ACTUAL07_TAIL_EARLY15_EXACT_REVIEW_CANONICAL01.json",
)
CORE = "third_party/ccl-framework/core/"
INCLUDE = "uc-library/include/presonus/"
SOURCE = "uc-library/src/Presonus/"
BOOK = (INCLUDE + "panel/Book.hpp", SOURCE + "Panel/Book.cpp")
ELEMENT = (INCLUDE + "panel/Element.hpp", SOURCE + "Panel/Element.cpp")
OFFSCREEN = (INCLUDE + "panel/OffscreenElement.hpp", SOURCE + "Panel/OffscreenElement.cpp")
BITMAP = (
    INCLUDE + "surface_panel/IDisplay.hpp",
    INCLUDE + "surface_panel/BitmapDrawing.hpp",
    "uc-library/src/surface_panel/BitmapDrawing.cpp",
)
VERIFIED_PROVIDERS = P / "ACTUAL07-LIVE-EXACT-PROVIDER-READBACK01.json"


def normalize_review_evidence(value):
    """Accept only verified checkout-contained absolute evidence and preserve its digest."""
    if isinstance(value, list):
        return [normalize_review_evidence(item) for item in value]
    if not isinstance(value, dict):
        return value
    result = {key: normalize_review_evidence(item) for key, item in value.items()}
    path_value = result.get("path")
    if isinstance(path_value, str) and Path(path_value).is_absolute():
        path = Path(path_value)
        digest = result.get("sha256")
        if (not path.is_relative_to(ROOT) or path.resolve(strict=True) != path or not path.is_file()
                or not isinstance(digest, str) or sha(path) != digest):
            raise ValueError("Unsafe absolute evidence reference " + path_value)
        result["path"] = str(path.relative_to(ROOT))
    return result


def ccl(name):
    return tuple(CORE + name + suffix for suffix in (".h", ".cpp"))


def formatter(name):
    return (INCLUDE + "mixer/" + name + ".hpp", SOURCE + "Mixer/" + name + ".cpp", *ccl("public/coreformatter"))


def actual_reference(path):
    kind = "provider_source" if path.startswith(CORE) else (
        "cpp_implementation" if Path(path).suffix == ".cpp" else "cpp_declaration")
    return reference(ROOT / path, kind, "Verified current typed provider")


def selected_role(task):
    if task == "cycle20_g08_s20":
        return BOOK + ccl("portable/corecomponent") + ccl("portable/coreparams")
    if task in ("cycle20_g05_s20", "cycle20_g09_s20"):
        return formatter("PreDelayFormatter")
    if task == "cycle20_g05_s19":
        return formatter("EarlyRefFormatter")
    if task in ("cycle20_g10_s09", "cycle20_g10_s12"):
        return OFFSCREEN + ELEMENT
    if task == "cycle20_g10_s10":
        return ELEMENT
    if task == "cycle20_g10_s11":
        return ELEMENT + BITMAP
    assert task == "cycle20_g09_s07", task
    return ()


def exact_lower_boundary(task, boundary):
    observation = boundary["observed"]
    names = boundary["routing_context"]["target_names"]
    if observation["kind"] == "ARM_INDIRECT_REVIEW_CANDIDATE":
        assert task == "cycle20_g10_s11" and observation["site"] in {123020, 619772}
        return "existing_implementation", "BitmapDisplay::fillRect", BITMAP, (
            "Replay the exact native offline IDisplay vslot +0x24 and compare the real typed BitmapDisplay provider. "
            "Observe passed rectangle and raster bounds on an in-memory bitmap.")
    assert len(names) == 1, names
    name = names[0]
    if name == "Presonus::Panel::Book::Book(int)":
        return "existing_implementation", name, BOOK, "Use and replay the real already admitted typed Book constructor."
    if name == "Presonus::Panel::Book::~Book()":
        return "existing_implementation", name, BOOK, "Observe native cleanup only for the Book constructed on the relevant unwind branch."
    if name.startswith("Core::Portable::Component::"):
        return "pinned_provider", name, ccl("portable/corecomponent"), "Use the real pinned CCL Component lifetime and independently observe its scope."
    if name.startswith("Core::Portable::ParamList::add("):
        return "pinned_provider", name, ccl("portable/coreparams"), "Bind the real pinned ParamList and reconstruct only the exact three application registrations."
    if name == "Presonus::Panel::Element::Element(int, int)":
        return "existing_implementation", name, ELEMENT, "Independently match the already admitted typed Element base initializer order and values."
    if name == "Presonus::Panel::OffscreenElement::OffscreenElement(int, int)":
        return "existing_implementation", name, OFFSCREEN, "Independently match the existing typed OffscreenElement base constructor and its ownership."
    if name == "__cxa_end_cleanup@@CXXABI_1.3":
        return "existing_implementation", name, (), "Native unwind runtime boundary only. Compare exact constructed-provider cleanup and leave unwinding to the real host runtime."
    if name == "operator delete(void*)@@GLIBCXX_3.4":
        return "existing_implementation", name, (), "Observe actual same-receiver unsized native deallocation; independently check genuine host teardown and operator delete."
    if name == "strcpy@@GLIBC_2.4":
        return "existing_implementation", name, (), "Observe the exact native local label strings in their bounded destination domain; preserve genuine typed owned string behavior."
    raise ValueError(f"Unreviewed exact provider for {task}: {name}")


def local_review(row):
    task, candidate = row["task_id"], row["candidate"]
    native = candidate["native_lifecycle_observation"]
    assert sha(ROOT / native["path"]) == native["sha256"]
    original = dict(native, kind="review_record", scope="Separately executed exact native role evidence")
    evidence = [original]
    providers = sorted(set(selected_role(task)) | set(candidate.get("frozen_provider_files") or {}))
    evidence.extend(actual_reference(name) for name in providers)
    if task != "cycle20_g09_s07":
        evidence.append(reference(VERIFIED_PROVIDERS, "review_record", "Live exact canonical predecessor evidence"))
    for item in candidate.get("reviewed_native_boundary_proof", []):
        assert sha(ROOT / item["path"]) == item["sha256"]
        evidence.append(dict(item, kind="review_record", scope="Reviewed role/ABI and original application observations"))
    objective = candidate["bounded_selection_work"]
    work = dict(
        objective=objective, owned_files=row["production"],
        oracle_plan="Execute every original role/range independently and compare actual typed host inputs, behavior and source provider effects.",
    )
    boundaries = {}
    for key, boundary in row["boundaries"].items():
        kind, provider, files, reason = exact_lower_boundary(task, boundary)
        boundaries[key] = dict(kind="dependency", reason=reason, dependency=dict(
            kind=kind, name=provider, binding_domain=reason,
            evidence=[original, *(actual_reference(path) for path in files)]))
    return dict(
        target=row["target"], work_item_id=candidate["work_item_id"], native_evidence_sha256=row["native"]["sha256"],
        reviewer="Root-approved Actual07 exact native and portable provider scope",
        namespace=candidate["scope"], objective=objective,
        domain="Exact offline application role and genuine canonical typed provider domain.",
        requirements={
            name: dict(status="bounded_work", reason=objective, evidence=evidence, work=work)
            for name in ("declarations", "state", "lifecycle", "providers")
        },
        execution_boundaries=boundaries, extra_source_reads=providers,
    )


def main():
    wave = int(sys.argv[1])
    revision = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    assert revision >= 2
    assert wave in (1, 2) and sha(AUTHORITY) == AUTHORITY_SHA
    approval = read(AUTHORITY)
    assert approval["active"] == read(ROOT / "dependency-graph/ACTIVE.json")
    assert approval["active"]["state_sha256"] == GENERATION
    guard(ROOT, approval["active"])
    phase = approval["phases"][wave - 1]
    prefix = f"actual07-authorized-wave{wave:02}"
    inventory = P / (prefix + ("-inventory02/INVENTORY.json" if wave == 2 else "-inventory01/INVENTORY.json"))
    configured = P / (prefix + f"-review-current{revision:02}.json")
    output = P / (prefix + f"-plans{revision:02}")
    batch = P / (prefix + f"-capture{revision:02}")
    authorized = {item["task"]: item for rows in phase["owners"].values() for item in rows}
    all_rows = {row["task_id"]: row for lane in read(inventory)["lanes"] for row in lane["tasks"]}
    assert set(authorized) == set(all_rows)
    copy = read(COPY)
    transitions = {row["path"]: dict(previous_draft=row["before"], current_canonical=row["after"])
                   for row in copy["files"] if Path(row["path"]).suffix in {".h",".hpp",".cpp"}}
    transitions.update({str(ROOT / path): delta for path, delta in list(transitions.items())})
    available = {}
    for file in REVIEW_FILES:
        available.update(read(file)["tasks"])
    reviews = {}
    for name, row in all_rows.items():
        wanted = authorized[name]
        assert row["targets"] == wanted["originals"]
        assert row["candidate"]["work_item_id"] == wanted["work_item_id"]
        assert sorted(row["production"]) == sorted(wanted["owned_files"])
        if name in available:
            review = renewed_site(available[name], transitions)
            assert review["work_item_id"] == wanted["work_item_id"], name
            assert review["native_evidence_sha256"] == row["native"]["sha256"], name
            assert set(review["execution_boundaries"]) == set(row["boundaries"]), name
            changed = set(wanted["source_sha256"]) & transitions.keys()
            if changed:
                for path in changed:
                    actual = sha(ROOT / path)
                    assert actual == wanted["source_sha256"][path] == transitions[path]["current_canonical"], path
                binding = reference(COPY, "review_record", "Exact applied canonical source transition")
                for requirement in review["requirements"].values():
                    requirement["evidence"].append(binding)
        else:
            review = local_review(row)
        reviews[name] = normalize_review_evidence(review)

    authority = (
        f"Root explicitly approved exact Actual07 wave {wave}, {phase['count']} works from 67/139, "
        f"authority {AUTHORITY_SHA} at graph {GENERATION}. Keep reader releases "
        "G04 and first G05 before G10, G08 before G07, and serial G05 groups."
    )
    save(configured, dict(tasks=reviews, smaller_batch_authorization=authority,
                         production_continuation=authority,
                         reviewed_authority=reference(AUTHORITY, "review_record", "Exact owner, scope and order")))
    materialize(inventory, configured, output, batch)
    task_list = output / "TASKS.json"
    final = read(task_list)
    assert len(final["tasks"]) == phase["count"]
    assert {
        g["task_name"]: [Path(path).name for path in g["execution_order"]] for g in final["groups"]
    } == {name: [row["task"] for row in rows] for name, rows in phase["owners"].items()}
    requests = [read(ROOT / path) for path in final["tasks"]]
    with batch_validation(ROOT):
        for request in requests:
            wanted = authorized[request["task_id"]]
            assert request["targets"] == wanted["originals"]
            assert request["existing_work_item_id"] == wanted["work_item_id"]
            for path in bound_files(ROOT, request):
                assert inside(ROOT, path).is_file(), path
            validate_request(ROOT, request)
    verify_planned_equivalence(requests)
    print(task_list, sha(task_list), len(requests), sum(len(row["targets"]) for row in requests))


if __name__ == "__main__":
    main()
