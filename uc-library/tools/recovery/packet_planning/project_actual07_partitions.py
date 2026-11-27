"""Read-only projection of Actual07 ownership and pre-copy compiler inputs."""
from collections import defaultdict
from itertools import combinations
from pathlib import Path
import re

from packet_cycle import CYCLE, ROOT, read, rel, save
from context_runtime import sha

S = CYCLE / "selection"
P = CYCLE / "packeting"
BUILD = ROOT / "temp/core-upstream/root-integration-01"
PROJECT = S / "ACTUAL07_COMBINED_41_PROJECTION01.json"
TYPED = S / "ACTUAL07_TYPED_G02_G03_MAX13_PROPOSAL01.json"
TYPED_REVIEW = S / "ACTUAL07_TYPED_G02_G03_MAX13_REVIEW_PREVIEW01.json"
MATRIX = S / "ACTUAL07_PROSPECTIVE_CANDIDATE_MATRIX01.json"
COPY = CYCLE / "integration/preview-actual06-next42/PLAN.json"


def ref(path):
    return dict(path=rel(path), sha256=sha(path))


def scoped_proposals(path):
    return {
        row["task_id_override"]: (
            row, next(scope for scope in lane["scope_ownership"] if scope["scope"] == row["scope"])
        )
        for lane in read(path)["lanes"] for row in lane["candidates"]
    }


def source_paths(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key in ("path", "file"):
                yield from source_paths(item)
            elif isinstance(item, (list, dict)):
                yield from source_paths(item)
    elif isinstance(value, list):
        for item in value:
            yield from source_paths(item)
    elif isinstance(value, str) and value.startswith(("uc-library/", "third_party/")):
        if Path(value).suffix in (".h", ".hpp", ".cc", ".cpp"):
            yield value


def previous_compiler_deps(sources):
    for source in sources:
        if not source.startswith("uc-library/src/") or Path(source).suffix != ".cpp":
            continue
        suffix = source.removeprefix("uc-library/") + ".o.d"
        for depfile in BUILD.glob("CMakeFiles/*.dir/" + suffix):
            content = depfile.read_text().replace("\\\n", " ")
            entries = [
                name.removeprefix(str(ROOT) + "/") for name in re.findall(r"[^\s]+", content)
                if name.startswith(str(ROOT) + "/")
            ]
            yield ref(depfile), {path for path in entries if Path(path).suffix in (".h", ".hpp", ".cpp")}


def exact_dependency_ids(review, by_work):
    result = set()
    for item in review.get("additional_dependencies", []):
        if item["kind"] == "included_work":
            result.add(by_work[item["work_item_id"]])
    for site in review.get("execution_boundaries", {}).values():
        dependency = site.get("dependency", {})
        if dependency.get("kind") == "included_work":
            result.add(by_work[dependency["work_item_id"]])
    return result


def topological_group(group, tasks):
    ordered = []
    remaining = set(group)
    while remaining:
        ready = [name for name in group if name in remaining and
                 set(tasks[name]["same_capture_prerequisites"]) <= set(ordered)]
        if not ready:
            raise ValueError("Unresolved work prerequisites in group " + repr(sorted(remaining)))
        ordered.extend(ready)
        remaining.difference_update(ready)
    return ordered


def main():
    projected = read(PROJECT)
    matrix = read(MATRIX)["work"]
    source_copy = read(COPY)
    copy_paths = {item["path"]: item for item in source_copy["files"]}
    typed = scoped_proposals(TYPED)
    typed_reviews = read(TYPED_REVIEW)["tasks"]
    work_to_task = {row["work_item_id"]: name for name, (row, _) in typed.items()}
    rows = {}
    for task_id in projected["planned"]["current"] + projected["planned"]["after_canonical"]:
        if task_id in typed:
            continue
        current = matrix[task_id]
        path = ROOT / current["receipt"]["path"]
        assert sha(path) == current["receipt"]["sha256"]
        rows[task_id] = (*scoped_proposals(path)[task_id], path)
    rows.update({key: (*value, TYPED) for key, value in typed.items()})
    assert len(rows) == 52

    tasks = {}
    for task_id, (candidate, ownership, source) in rows.items():
        owned = sorted(set(ownership["owned_headers"] + ownership["owned_sources"]))
        review = typed_reviews.get(task_id, {})
        reads = set(candidate.get("frozen_provider_files", {})) | set(source_paths(review))
        previous = sorted(set(candidate.get("accepted_predecessor_task_ids", [])) |
                          set(matrix.get(task_id, {}).get("prerequisite_ids", [])))
        included = exact_dependency_ids(review, work_to_task) - {task_id}
        # External already-accepted providers and included local producers require distinct proof.
        for provider in set(previous) & rows.keys():
            included.add(provider)
        depfiles = list(previous_compiler_deps(owned))
        observed = set().union(*(paths for _, paths in depfiles))
        future_paths = set(owned) | reads | observed
        evidence = candidate.get("reviewed_native_boundary_proof") or []
        tasks[task_id] = dict(
            proposal=ref(source),
            upstream_work_id=candidate["work_item_id"],
            owner="_".join(task_id.split("_")[:2]),
            owned=owned,
            declared_reads=sorted(reads),
            historical_compiler_reads=sorted(observed),
            historical_depfiles=[value for value, _ in depfiles],
            previous_prerequisites=sorted(set(previous) - rows.keys()),
            same_capture_prerequisites=sorted(included),
            current_guarded_native_provider_evidence=evidence,
            projected_canonical_copy_hits={
                name: dict(before=copy_paths[name]["before"], after=copy_paths[name]["after"],
                           path_kind=("owned" if name in owned else "declared_read" if name in reads else "previous_compiler_read"))
                for name in sorted(future_paths & copy_paths.keys())
            },
        )

    g05 = projected["same_g05_owner_phase_partition"]
    chunks = {key: list(value) for key, value in g05.items()}
    for task, row in tasks.items():
        if row["owner"] != "cycle20_g05":
            chunks.setdefault(row["owner"], []).append(task)
    assert set(tasks) == {task for chunk in chunks.values() for task in chunk}
    assert all(0 < len(group) <= 10 for group in chunks.values())
    chunks = {name: topological_group(group, tasks) for name, group in chunks.items()}
    group_writes = {n: set().union(*(set(tasks[t]["owned"]) for t in members)) for n, members in chunks.items()}
    group_reads = {
        n: set().union(*(set(tasks[t]["declared_reads"]) for t in members)) for n, members in chunks.items()
    }
    group_observed = {
        n: set().union(*(set(tasks[t]["historical_compiler_reads"]) for t in members)) for n, members in chunks.items()
    }
    conflicts = []
    for first, second in combinations(sorted(chunks), 2):
        write_overlap = group_writes[first] & group_writes[second]
        exact = (group_writes[first] & group_reads[second]) | (group_writes[second] & group_reads[first])
        observed = (group_writes[first] & group_observed[second]) | (group_writes[second] & group_observed[first])
        same_owner = chunks[first][0].split("_")[1] == chunks[second][0].split("_")[1]
        if write_overlap or exact or observed or same_owner:
            conflicts.append(dict(first=first, second=second, shared_writes=sorted(write_overlap),
                                  declared_conflicts=sorted(exact), observed_compiler_conflicts=sorted(observed),
                                  same_owner=same_owner))
    output = P / "ACTUAL07-PRECOPY-PARTITION-PROJECTION01.json"
    save(output, dict(
        scope="Projected pre-copy only. Current graph or dispatch status is not inferred.",
        proofs=dict(project=ref(PROJECT),typed=ref(TYPED),typed_review=ref(TYPED_REVIEW),
                    candidate_matrix=ref(MATRIX),canonical_copy=ref(COPY)),
        tasks=tasks, logical_chunks=chunks, conflict_projection=conflicts,
        candidate_count=len(tasks), captures=0, claims=0,
    ))
    print(output, sha(output))
    print("Legal owner chunks", {name:len(group) for name, group in chunks.items()})
    for row in conflicts:
        print(row)


if __name__ == "__main__":
    main()
