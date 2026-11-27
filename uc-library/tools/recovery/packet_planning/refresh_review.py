"""Rebind review source observations after a coordinated canonical apply."""
from pathlib import Path
import sys

from packet_cycle import read, reference, save


def refresh(node):
    if isinstance(node, list):
        return [refresh(value) for value in node]
    if not isinstance(node, dict):
        return node
    if {"path", "sha256", "kind", "scope"} <= node.keys():
        current = reference(node["path"], node["kind"], node["scope"])
        if current != node and Path(node["path"]).suffix not in {".h", ".hpp", ".cpp"}:
            raise ValueError("Non-source review reference changed: " + node["path"])
        return current
    return {key: refresh(value) for key, value in node.items()}


if __name__ == "__main__":
    source, out = map(Path, sys.argv[1:])
    save(out, refresh(read(source)))
