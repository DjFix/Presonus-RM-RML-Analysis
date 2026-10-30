#!/usr/bin/env python3
"""Read Ethernet pcapng, reassemble captured TCP bytes and export UC test vectors."""
import argparse
import collections
import hashlib
import json
import struct
from pathlib import Path


def packets(path):
    raw = path.read_bytes()
    offset, endian = 0, '<'
    interfaces = []
    while offset+12 <= len(raw):
        if raw[offset:offset+4] == b'\x0a\x0d\x0d\x0a':
            endian = '<' if raw[offset+8:offset+12] == b'\x4d\x3c\x2b\x1a' else '>'
            interfaces = []
        kind, length = struct.unpack_from(endian+'II', raw, offset)
        if length < 12 or offset+length > len(raw) or struct.unpack_from(endian+'I', raw, offset+length-4)[0] != length:
            raise ValueError(f'invalid pcapng block at {offset}')
        body = raw[offset+8:offset+length-4]
        if kind == 1:
            interfaces.append(struct.unpack_from(endian+'H', body)[0])
        elif kind == 6:
            interface, hi, lo, captured, original = struct.unpack_from(endian+'IIIII', body)
            if interfaces[interface] != 1:
                raise ValueError('only Ethernet capture interfaces supported')
            yield body[20:20+captured]
        offset += length


def transport(frame):
    if len(frame)<14:
        return
    protocol = int.from_bytes(frame[12:14], 'big')
    start = 14
    while protocol in (0x8100, 0x88a8):
        protocol = int.from_bytes(frame[start+2:start+4], 'big')
        start += 4
    if protocol != 0x800 or len(frame)<start+20:
        return
    ip = frame[start:]
    if int.from_bytes(ip[6:8], 'big') & 0x3fff:
        return  # Explicitly exclude fragmented IP, rather than misparse it.
    size = int.from_bytes(ip[2:4], 'big')
    body = ip[(ip[0]&15)*4:size]
    if len(body)<8:
        return
    src, dst = ('.'.join(map(str,ip[i:i+4])) for i in (12,16))
    sport, dport = struct.unpack_from('!HH', body)
    if ip[9] == 17:
        yield 'udp', (src,sport,dst,dport), 0, body[8:int.from_bytes(body[4:6],'big')]
    elif ip[9] == 6 and len(body)>=20:
        yield 'tcp', (src,sport,dst,dport), int.from_bytes(body[4:8],'big'), body[(body[12]>>4)*4:]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('capture', type=Path)
    p.add_argument('output', type=Path)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    streams = collections.defaultdict(dict)
    vectors, stats, tags = [], collections.Counter(), collections.Counter()
    for frame in packets(a.capture):
        stats['packets'] += 1
        for proto, flow, seq, payload in transport(frame) or ():
            if proto == 'udp' and payload.startswith(b'UC\x00\x01') and len(payload)>=12:
                vectors.append(dict(transport='udp', flow=flow, hex=payload.hex()))
            elif proto == 'tcp' and payload:
                old = streams[flow].get(seq)
                if old is not None and old != payload:
                    stats['conflicting_retransmissions'] += 1
                streams[flow][seq] = payload
    for flow, segments in streams.items():
        data, end = bytearray(), None
        for seq, payload in sorted(segments.items()):
            if end is not None and seq>end:
                stats['tcp_gaps'] += 1
                break
            skip = max(0, end-seq) if end is not None else 0
            data.extend(payload[skip:])
            end = max(end or 0, seq+len(payload))
        offset = 0
        if not data.startswith(b'UC\x00\x01'):
            continue
        while offset+6<=len(data):
            if data[offset:offset+4] != b'UC\x00\x01':
                stats['bad_stream_headers'] += 1
                break
            length = int.from_bytes(data[offset+4:offset+6], 'little')
            if length<6 or length>0x4000 or offset+6+length>len(data):
                stats['incomplete_or_invalid_frames'] += 1
                break
            vectors.append(dict(transport='tcp', flow=flow, hex=data[offset:offset+6+length].hex()))
            offset += 6+length
    unique = {}
    for vector in vectors:
        raw = bytes.fromhex(vector['hex'])
        tag = raw[6:8].decode('ascii', errors='replace')
        tags[tag] += 1
        stats[vector['transport']+'_frames'] += 1
        unique.setdefault((vector['transport'], vector['hex']), vector)
    stats['unique_vectors'] = len(unique)
    report = dict(capture=str(a.capture), sha256=hashlib.sha256(a.capture.read_bytes()).hexdigest(),
                  stats=dict(stats), event_tags=dict(tags), vectors=list(unique.values()))
    (a.output/'capture-vectors.json').write_text(json.dumps(report, indent=2)+'\n')
    # Portable C++ test input, one captured frame per line.
    (a.output/'capture-vectors.txt').write_text(''.join(v['transport']+' '+v['hex']+'\n' for v in unique.values()))
    print(json.dumps({k:v for k,v in report.items() if k!='vectors'}, indent=2))


if __name__ == '__main__':
    main()
