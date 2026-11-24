"""Check archived predecessor and current bytes for explicit CTest source transitions."""
from hashlib import sha256
import json
from pathlib import Path


def _sha(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def load_transition(path, expected_sha256):
    if path is None and expected_sha256 is None:
        return {}
    assert path is not None and expected_sha256 and _sha(path) == expected_sha256
    rows = json.loads(Path(path).read_text())["source_transitions"]
    result = {}
    for row in rows:
        logical = Path("uc-library") / row["path"]
        assert logical not in result and not logical.is_absolute() and ".." not in logical.parts
        assert _sha(row["previous_frozen_read_path"]) == row["previous_sha256"], logical
        assert _sha(row["current_frozen_read_path"]) == row["current_sha256"], logical
        result[logical] = row
    return result


def current_source_digest(logical, previous, transitions):
    row = transitions.get(Path(logical))
    if row is None:
        return previous
    assert row["previous_sha256"] == previous, logical
    return row["current_sha256"]
