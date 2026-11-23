"""Chunked exact transport for the unchanged logical native candidate seal."""
import base64
import hashlib
import json
import zlib

from context_runtime import ContextError

CODEC = "owner-atoms-chunked-zlib-base64-v3"
MAINTENANCE_CODEC = "owner-atoms-chunked-zlib-base64-v3-maintenance"
CODECS = (CODEC, MAINTENANCE_CODEC)
MAX_CHUNK = 1024 * 1024
MAX_PACKED = 256 * 1024 * 1024
MAX_LOGICAL = 1024 * 1024 * 1024
MAX_MAINTENANCE_PACKED = MAX_LOGICAL
MAX_CHUNKS = 1024
SECTIONS = ("header", "atoms", "pools", "affected_ids", "sources", "native_nodes", "expected", "native_inputs")
SPLIT = SECTIONS[3:]
ENCODER = json.JSONEncoder(sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canon(data):
    return ENCODER.encode(data).encode()


def sized_digest(value, limit=MAX_LOGICAL):
    total = 0
    digest = hashlib.sha256()
    for token in ENCODER.iterencode(value):
        raw = token.encode()
        total += len(raw)
        if total > limit:
            raise ContextError("Native candidate logical guard exceeds its explicit bound")
        digest.update(raw)
    return total, digest.hexdigest()


def manifest_digest(chunks):
    return sized_digest([tuple(chunk[key] for key in ("index", "bytes", "sha256", "compressed_bytes", "compressed_sha256"))
                         for chunk in chunks], MAX_CHUNKS * 300)[1]


def records(seal):
    atoms, indices, pools, pool_indices = [], {}, [], {}
    source_pool_ids = []
    for source in seal["sources"]:
        if type(source) is not dict or set(source) != {"owners", "properties"}:
            raise ContextError("Invalid guard source")
        owners = source["owners"]
        if type(owners) is not list or any(type(owner) is not str for owner in owners):
            raise ContextError("Invalid owner list")
        refs = []
        for owner in owners:
            if owner not in indices:
                indices[owner] = len(atoms)
                atoms.append(owner)
            refs.append(indices[owner])
        key = tuple(refs)
        if key not in pool_indices:
            pool_indices[key] = len(pools)
            pools.append(refs)
        source_pool_ids.append(pool_indices[key])
    yield "header", {key:value for key,value in seal.items() if key not in SPLIT}
    for atom in atoms:
        yield "atoms", atom
    for pool in pools:
        yield "pools", pool
    for key in SPLIT:
        if key == "sources":
            for source, ref in zip(seal[key], source_pool_ids, strict=True):
                yield key, [source["properties"], ref]
        elif key == "native_nodes":
            for item in sorted(seal[key].items()):
                yield key, item
        else:
            for row in seal[key]:
                yield key, row


def pack(seal, logical_measure=None, *, maintenance=False):
    if type(seal) is not dict or seal.get("version") != 1:
        raise ContextError("Invalid logical v3 guard")
    logical_size, logical_sha = logical_measure or sized_digest(seal)
    packed_limit = MAX_MAINTENANCE_PACKED if maintenance else MAX_PACKED
    codec = MAINTENANCE_CODEC if maintenance else CODEC
    chunks, buffer = [], bytearray()
    packed_bytes = 0
    compressed_bytes = 0

    def emit():
        nonlocal compressed_bytes
        payload = zlib.compress(buffer, 6)
        compressed_bytes += len(payload)
        if len(chunks) >= MAX_CHUNKS or compressed_bytes > MAX_PACKED:
            raise ContextError("Native guard compressed chunk budget exceeded")
        chunks.append(dict(index=len(chunks), bytes=len(buffer), sha256=sha(buffer),
                           compressed_bytes=len(payload), compressed_sha256=sha(payload),
                           data=base64.b64encode(payload).decode("ascii")))
        buffer.clear()

    for record in records(seal):
        encoded = canon(record) + b"\n"
        packed_bytes += len(encoded)
        if len(encoded) > MAX_CHUNK:
            raise ContextError(f"Native guard {record[0]} record exceeds bounded chunk: {len(encoded)} bytes")
        if packed_bytes > packed_limit:
            raise ContextError(f"Native guard total raw chunks exceed {packed_limit} bytes at {packed_bytes} bytes")
        if len(buffer) + len(encoded) > MAX_CHUNK:
            emit()
        buffer.extend(encoded)
    if buffer:
        emit()
    return dict(guard_codec=codec, logical_bytes=logical_size, logical_sha256=logical_sha,
                packed_bytes=packed_bytes, chunk_manifest_sha256=manifest_digest(chunks), chunks=chunks)


def digest_is_valid(value):
    return type(value) is str and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def positive_count(value, maximum):
    return type(value) is int and 0 < value <= maximum


def chunk_payload(chunk):
    declared = chunk["compressed_bytes"]
    text = chunk["data"]
    if (not positive_count(declared, MAX_CHUNK + 1024) or type(text) is not str
            or len(text) != 4 * ((declared + 2) // 3)):
        raise ContextError("Invalid native guard compressed chunk length")
    compressed = base64.b64decode(text, validate=True)
    if len(compressed) != declared or sha(compressed) != chunk["compressed_sha256"]:
        raise ContextError("Native guard compressed chunk SHA mismatch")
    decoder = zlib.decompressobj()
    raw = decoder.decompress(compressed, chunk["bytes"] + 1)
    if (len(raw) != chunk["bytes"] or not decoder.eof or decoder.unused_data
            or decoder.unconsumed_tail or sha(raw) != chunk["sha256"] or not raw.endswith(b"\n")):
        raise ContextError("Native guard chunk range/hash mismatch")
    return raw


def unpack(envelope):
    if (type(envelope) is not dict or set(envelope) != {
            "guard_codec", "logical_bytes", "logical_sha256", "packed_bytes", "chunk_manifest_sha256", "chunks"}
            or envelope["guard_codec"] not in CODECS):
        raise ContextError("Invalid native guard v3 envelope")
    packed_limit = MAX_MAINTENANCE_PACKED if envelope["guard_codec"] == MAINTENANCE_CODEC else MAX_PACKED
    chunks = envelope["chunks"]
    if (not positive_count(envelope["logical_bytes"], MAX_LOGICAL) or
            not positive_count(envelope["packed_bytes"], packed_limit) or
            not digest_is_valid(envelope["logical_sha256"]) or
            not digest_is_valid(envelope["chunk_manifest_sha256"]) or type(chunks) is not list or
            not positive_count(len(chunks), MAX_CHUNKS)):
        raise ContextError("Invalid native guard v3 aggregate bounds")
    for index, chunk in enumerate(chunks):
        if (type(chunk) is not dict or set(chunk) != {"index","bytes","sha256","compressed_bytes","compressed_sha256","data"}
                or type(chunk["index"]) is not int or chunk["index"] != index
                or not positive_count(chunk["bytes"], MAX_CHUNK)
                or not positive_count(chunk["compressed_bytes"], MAX_CHUNK + 1024)
                or not digest_is_valid(chunk["sha256"]) or not digest_is_valid(chunk["compressed_sha256"])):
            raise ContextError("Invalid or reordered native guard chunk")
    if (sum(chunk["bytes"] for chunk in chunks) != envelope["packed_bytes"]
            or sum(chunk["compressed_bytes"] for chunk in chunks) > MAX_PACKED
            or manifest_digest(chunks) != envelope["chunk_manifest_sha256"]):
        raise ContextError("Native guard chunk manifest mismatch")

    section_id = 0
    seal, atoms, pools, pool_sizes = None, [], [], []
    atom_lengths = []
    lower_bound = 0
    for chunk in chunks:
        for line in chunk_payload(chunk).splitlines():
            record = json.loads(line)
            if type(record) is not list or len(record) != 2 or record[0] not in SECTIONS:
                raise ContextError("Invalid native guard record")
            key, value = record
            current = SECTIONS.index(key)
            if current < section_id or (seal is None and key != "header"):
                raise ContextError("Invalid native guard record section order")
            section_id = current
            if key == "header":
                if seal is not None or type(value) is not dict or set(SPLIT) & value.keys() or value.get("version") != 1:
                    raise ContextError("Invalid native guard v3 header")
                seal = dict(value, **{field: [] for field in SPLIT})
                seal["native_nodes"] = {}
            elif key == "atoms":
                if type(value) is not str:
                    raise ContextError("Invalid native guard owner atom")
                atoms.append(value)
                atom_lengths.append(len(canon(value)))
            elif key == "pools":
                if type(value) is not list or any(type(ref) is not int or not 0 <= ref < len(atoms) for ref in value):
                    raise ContextError("Invalid native guard owner atom reference")
                pools.append([atoms[ref] for ref in value])
                pool_sizes.append(2 + sum(atom_lengths[ref] for ref in value) + max(0, len(value)-1))
            elif key == "sources":
                if (type(value) is not list or len(value) != 2 or type(value[0]) is not dict
                        or type(value[1]) is not int or not 0 <= value[1] < len(pools)):
                    raise ContextError("Invalid native guard source owner reference")
                props, reference = value
                lower_bound += len(line) + pool_sizes[reference] - len(canon(reference)) - 2
                if lower_bound > envelope["logical_bytes"] + envelope["packed_bytes"]:
                    raise ContextError("Native guard owner expansion exceeds logical bound")
                seal[key].append({"properties": props, "owners": pools[reference]})
            elif key == "native_nodes":
                if (type(value) is not list or len(value) != 2 or type(value[0]) is not str
                        or type(value[1]) is not dict or value[0] in seal[key]):
                    raise ContextError("Duplicate/invalid native guard native node")
                seal[key][value[0]] = value[1]
            else:
                seal[key].append(value)
    if seal is None or sized_digest(seal, envelope["logical_bytes"]) != (envelope["logical_bytes"], envelope["logical_sha256"]):
        raise ContextError("Native guard expanded logical digest mismatch")
    return seal
