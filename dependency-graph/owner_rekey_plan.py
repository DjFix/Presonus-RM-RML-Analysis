"""Pair one old and one current compiler owner only by exact TU/build output."""
from collections import defaultdict
from pathlib import Path


def unit_key(owner, file, directory, output):
    if not all(isinstance(part, str) and part for part in (file, directory, output)):
        return None
    base = Path(directory).resolve()
    group = owner.partition(':')[0]
    return group, (base / file).resolve(), (base / output).resolve()


def pair_removed_owners(connection, removed, selected):
    retired, incoming = defaultdict(list), defaultdict(list)
    removed = set(removed)
    for owner, file, directory, output in connection.execute("""
        SELECT owner,json_extract(payload,'$.command.file'),
          json_extract(payload,'$.command.directory'),json_extract(payload,'$.command.output')
        FROM units
    """):
        if owner in removed:
            retired[unit_key(owner, file, directory, output)].append(owner)
    for owner, row in selected:
        incoming[unit_key(owner, row['file'], row['directory'], row.get('output'))].append(owner)
    paired = {}
    for identity in retired.keys() & incoming.keys():
        old, new = retired[identity], incoming[identity]
        if identity is not None and len(old) == len(new) == 1:
            paired[new[0]] = old[0]
    return paired
