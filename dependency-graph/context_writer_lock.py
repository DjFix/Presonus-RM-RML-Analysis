"""Exclusive host lock for supported graph mutation command entrypoints.

Internal publication functions are called only by a coordinator already holding
this lock. Do not acquire a second file description from a coordinated Docker
child: flock locks are not reentrant across separate file descriptions.
"""
from contextlib import contextmanager
import fcntl
import pathlib


@contextmanager
def exclusive_writer(root=None):
    root = pathlib.Path(root) if root is not None else pathlib.Path(__file__).resolve().parents[1]
    path = root / "dependency-graph/state/context.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        stream = path.open("r")  # Existing lock also works in read-only graph runner mounts.
    except FileNotFoundError:
        stream = path.open("a")
    with stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield stream
