"""Replay and isolate the original complete destructor results from both roles."""
import runpy
from pathlib import Path

RUNNER = Path(__file__).parent.parent / "sqlite06_reverb_fxtype_deleting_destroy/native.py"
RUNTIME = runpy.run_path(str(RUNNER))


def generate():
    results = []
    for case in RUNTIME["generate"]():
        results.append({
            "original": case["complete_original"],
            "complete_vptr": case["complete_vptr_before_d0"],
            "restored_core_vptr": case["vptr"],
            "receiver": case["guard"],
            "vptr_write": case["lifetime_vptr_writes"][0],
            "successful_allocation_after_d1": case["allocation_after_d1"],
            "deallocation_count": len(case["complete_delete_entries"]),
            "unicorn_version": case["unicorn_version"],
            "allocator": case["allocator"],
            "loader": case["loader"],
        })
    return results


if __name__ == "__main__":
    RUNTIME["cli"](generate)
