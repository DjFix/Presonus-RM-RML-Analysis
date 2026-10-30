#!/usr/bin/env python3
"""Original ARM UDP mapping, MIDI message and extension query payload fixtures."""
import argparse
import collections
import hashlib
import json
import struct
from pathlib import Path
import unicorn
from uc_event_oracle import make_oracle,call

METHODS=[
 ('_ZNK8Presonus2UC20UDPMappingEventClass5writeERNS0_12BufferWriterERKNS0_15UDPMappingEventE','udpWrite'),
 ('_ZNK8Presonus2UC20UDPMappingEventClass4readERNS0_15UDPMappingEventERNS0_12BufferReaderE','udpRead'),
 ('_ZNK8Presonus2UC21MidiMessageEventClass5writeERNS0_12BufferWriterERKNS0_16MidiMessageEventE','midiWrite'),
 ('_ZNK8Presonus2UC21MidiMessageEventClass4readERNS0_16MidiMessageEventERNS0_12BufferReaderE','midiRead'),
 ('_ZNK8Presonus2UC24ExtensionQueryEventClass5writeERNS0_12BufferWriterERKNS0_19ExtensionQueryEventE','extensionWrite'),
 ('_ZNK8Presonus2UC24ExtensionQueryEventClass4readERNS0_19ExtensionQueryEventERNS0_12BufferReaderE','extensionRead'),
]

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('repository',type=Path);a=p.parse_args()
    target=a.repository/'uc-library/validation/uc-transport';target.mkdir(parents=True,exist_ok=True)
    vectors=target/'arm-vectors.bin';assert not vectors.exists(),'preserve existing fixtures'
    records=0;counts=collections.Counter();failures=collections.Counter();originals=[]
    def pattern(seed):return bytes((i*29+seed*71)&255 for i in range(512))
    with vectors.open('wb') as output:
        output.write(b'UCTRv001'+struct.pack('<I',0))
        for role_id,role in enumerate(('client','server')):
            obj=make_oracle(a.repository,role)
            symbols=json.loads((a.repository/'uc-library/recovered'/role/'all-symbols.json').read_text())
            by_name={s['mangled']:s for s in symbols};obj.functions=[by_name[name] for name,_ in METHODS]
            def emit(op,capacity,offset,io,event):
                nonlocal records
                result,next_offset,out_io,out_event=call(obj,op,capacity,offset,io,event)
                if not result:
                    assert next_offset==offset and out_io==io and out_event==event,'non-atomic failure'
                output.write(struct.pack('<BBBBiii',role_id,op,result,0,capacity,offset,next_offset))
                output.write(io+event+out_io+out_event)
                key=role+':'+METHODS[op][1];counts[key]+=1
                if not result:failures[key]+=1
                records+=1
            for op in range(6):
                width=2 if op<2 else 4
                for capacity in range(33):
                    for offset in range(capacity+1):
                        for seed in range(4):emit(op,capacity,offset,pattern(seed),pattern(seed+1))
                for byte in range(width):
                    for value in range(256):
                        for remaining in (width-1,width):
                            io=bytearray(pattern(5));event=bytearray(pattern(6))
                            io[byte]=value;event[16+byte]=value
                            emit(op,remaining,0,bytes(io),bytes(event))
            originals.append(dict(role=role,elf_sha256=obj.manifest['sha256'],functions=obj.functions,helpers=dict(obj.helpers)))
            print(role,records,'ARM transport fixtures',flush=True)
        output.seek(8);output.write(struct.pack('<I',records))
    report=dict(records=records,cases=dict(counts),failure_cases=dict(failures),partial_mutation_failures={},originals=originals,
                vectors_sha256=hashlib.sha256(vectors.read_bytes()).hexdigest(),unicorn_version=unicorn.__version__,
                domain='Disjoint valid 512-byte IO/event images; every capacity0..32/cursor0..capacity, four seeded patterns; each payload byte exhausts0..255 at exact-capacity and one-byte-short boundaries. UDP LE16, MIDI four raw bytes, extension BE32. Invalid pointers, negative capacities/cursors, pointer wrap, memcpy alias/overlap, overflow and concurrency excluded.',
                dependencies='Original ARM payload functions execute; imported memcpy modeled by its standard contract, libc implementation excluded. Portable implementations reuse sealed BufferReader/Writer primitives.',
                limitations=['Portable event storage and bool declarations only; original field names/inheritance/layout/vtables/constructors and non-template return spelling unproved.','Payload only; common header/tag processing and EventItem dispatch excluded.','Hardware testing deferred.'])
    (target/'oracle.json').write_text(json.dumps(report,indent=2)+'\n')
    print(records,'ARM transport fixtures complete',flush=True)

if __name__=='__main__':main()
