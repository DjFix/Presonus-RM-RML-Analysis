"""Atomic batch launch barrier. Membership files contain no spawn arguments."""
import json
import os
import pathlib
import time

from context_runtime import ContextError, inside, sha


def atomic_json(path, value):
    temporary = path.with_name(path.name + '.new-' + str(time.time_ns()))
    with temporary.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def verify_packet_files(root, packets, expected_manifests=None):
    """Fresh publication barrier; no prior successful file check is reused."""
    for path in packets:
        packet_path = inside(root, str(path))
        relative = str(packet_path.relative_to(root))
        if expected_manifests is not None and sha(packet_path/'context.json') != expected_manifests[relative]:
            raise ContextError('Packet changed during batch validation: '+relative)
        packet = json.loads((packet_path/'context.json').read_text())
        if packet.get('state') != 'dispatch_ready':
            raise ContextError('Packet is not finalized')
        from native_context import require_nonempty
        require_nonempty(packet)
        for path, digest in packet['packet_sha256'].items():
            if sha(inside(packet_path,path)) != digest:
                raise ContextError('Packet artifact changed before publication: '+path)
        for field in ('selected_file_sha256','tool_sha256'):
            for path,digest in packet[field].items():
                if sha(inside(root,path)) != digest:
                    raise ContextError('Publication input changed: '+path)
        if sha(root/'AGENTS.md') != packet['agents_sha256']:
            raise ContextError('Instructions changed before publication')


def publish_batch(root, output, payload, packets):
    """Caller holds exclusive context lock and has freshly validated every input."""
    destination = output / 'BATCH_DISPATCH.json'
    if destination.exists():
        raise ContextError('Batch dispatch already published')
    paths = [inside(root, str(p)) for p in packets]
    manifests = {str(p.relative_to(root)): sha(p / 'context.json') for p in paths}
    if len(manifests) != len(paths) or not manifests:
        raise ContextError('Empty or duplicate publication packets')
    publication_id = str(time.time_ns())
    relative = str(destination.relative_to(root))
    for packet in paths:
        if (packet / 'DISPATCH.json').exists():
            raise ContextError('Packet already has standalone launch permission')
        member = packet / 'BATCH_MEMBER.json'
        if member.exists():
            previous = json.loads(member.read_text())
            if previous.get('manifest') != relative:
                raise ContextError('Packet belongs to another batch')
        atomic_json(member, {'version': 1, 'manifest': relative,
                             'publication_id': publication_id,
                             'context_sha256': manifests[str(packet.relative_to(root))]})
    sealed = dict(payload, publication_state='complete', publication_id=publication_id,
                  packet_manifests=manifests)
    atomic_json(destination, sealed)
    return destination


def authorization(root, packet):
    """Authenticate batch membership before allowing baseline expansion/reuse."""
    member = packet / 'BATCH_MEMBER.json'
    if member.exists():
        binding = json.loads(member.read_text())
        manifest = inside(root, binding['manifest'])
        if not manifest.is_file():
            raise ContextError('Batch publication incomplete; no launch permission')
        payload = json.loads(manifest.read_text())
        relative = str(packet.relative_to(root))
        digest = sha(packet / 'context.json')
        if (payload.get('publication_state') != 'complete' or
                payload.get('publication_id') != binding.get('publication_id') or
                binding.get('context_sha256') != digest or
                payload.get('packet_manifests', {}).get(relative) != digest):
            raise ContextError('Batch publication binding mismatch')
        return payload
    if not (packet / 'DISPATCH.json').is_file():
        raise ContextError('Packet has no completed dispatch publication')
    return json.loads((packet / 'DISPATCH.json').read_text())
