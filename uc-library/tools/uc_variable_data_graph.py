#!/usr/bin/env python3
"""Catalog UC variable-data declarations/dependencies; never mark Core pools ready."""
import argparse,hashlib,json
from pathlib import Path

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('library',type=Path);p.add_argument('repository',type=Path);a=p.parse_args();lib=a.library;repo=a.repository
 target=lib/'candidates/uc-variable-data';target.mkdir(parents=True,exist_ok=True)
 inventories={r:json.loads((lib/'recovered'/r/'all-symbols.json').read_text()) for r in ('client','server')}
 selected={}
 for role,inventory in inventories.items():
  entries=[]
  for s in inventory:
   name=s.get('demangled','')
   variable=name.startswith('Presonus::UC::DataEventClass<') or name.startswith(('Presonus::UC::BinaryEventClass::','Presonus::UC::MessageChunkEventClass::','Presonus::UC::FileDataEventClass::'))
   if variable and any(m in name for m in ('::read(', '::write(', '::create(', '::readDataBuffer(', '::writeDataBuffer(', '::getType(')):
    mode='pool-creation-pending' if '::create()' in name else 'requires-real-Core-buffer-and-owner-contract' if '::read(' in name and 'EventItem&' in name or '::readDataBuffer(' in name or '::create(' in name else 'wire-or-fixed-storage-analysis'
    entries.append(dict(symbol=s,status=mode))
  selected[role]=dict(manifest=json.loads((lib/'recovered'/role/'manifest.json').read_text()),inventory_sha256=sha(lib/'recovered'/role/'all-symbols.json'),functions=entries)
 paths=['third_party/ccl-framework/core/public/corebuffer.h','third_party/ccl-framework/core/public/corebuffer.cpp','third_party/ccl-framework/core/malloc/coremalloc.cpp']
 report=dict(source_commit='e8cbdea4a4a20e15111f5a690798a259c0374b31',source_tag='ccl5.0.0',source_files={n:sha(repo/n) for n in paths},
             source_status='Actual unmodified upstream API/body; source provision is not original ARM ABI/binary equivalence.',originals=selected,
             first_candidate='DataEventClass<EncodedMessageEvent<21826>,21826>::read/write/create(Eventconst&); isolated until actual nativeprovider link/smoke and app differential proof.',
             native_provider=dict(target='corelib + unmodified core/malloc/coremalloc.cpp',archive='temp/core-upstream/build-output/linux/Release/libcorelib.a',sha256='0b958004e35637fcb3ec8225c3b073e5187d6a86335675af03dbf8fe8a9d2be7',global_integration=False),
             ownership_rules=['Separate OwnedDataItem stores actual Core::IO::Buffer and a nonowning event view; delete copy/move on owner.','Never use default Buffer copy/assignment or existing TypedFactoryCodec shallow value assignment for owned variable data.','Explicit clone copies logical event fields, calls real resize and positive-signed-length copyFrom, ignores failures as original app, then resets view address to actual storage and preserves declared source length.','Read consumes LE32 length and invokes resize before payload-availability check; resize failure retains prior event view; successful resize updates view even when payload truncation then fails.','Empty null-data calls use existing BufferReader/Writer zero-count checks with valid scratch pointer; defined-state equivalence only, not external call/ABI trace.','Bounded actual allocator tests fail large requests before any real multi-GiB allocation. No original Core pool implementation is invented.'])
 (target/'dependency-graph.json').write_text(json.dumps(report,indent=2)+'\n')
 text='''# UC variable-data dependency graph (candidate, not integrated)

```mermaid
flowchart TD
  Factory[Existing portable EventFactory registry] --> Wire[Original UC wire codecs]
  Wire --> Header[Sealed common header and buffer methods]
  Wire --> Owner[Portable OwnedDataItem / explicit event view]
  Owner --> Real[Actual pinned Core::IO::Buffer]
  Real --> Alloc[Unmodified vendor coremalloc.cpp / bounded test allocator]
  Clone[Original UC create Event overload] --> Owner
  Clone --> Resize[Actual Buffer resize and copyFrom]
  Pool[Original no-argument create / DataItem / PooledDataItem] --> Pending[Original pools / constructor / ownership ABI pending]
```

## Declaration/definition groups

| Group | Original app value/wire observation | Ownership/definition boundary |
| --- | --- | --- |
| EncodedMessageEvent 19021 / 23117 / 21826 / 23106 | Header, nonowning pointer+16 and raw32 length+20; wire common header, LE32 length, bytes | Real Core buffer in separate owner; length framing does not decode JSON/compression |
| LoopbackQuery 19537 / LoopbackReply 19538 / MidiLongSysex 21324 | Same24-byte ARM value-view shape and generic data framing | No content/MIDI validation inferred; clone must deep-copy via actual Core API |
| BinaryEvent 16975 | Generic data view plus BE32 at+24 in derived BinaryEventClass wire codec | Generic DataEventClass base wire methods also exist; do not substitute one for derived metadata codec |
| MessageChunkEvent 17227 | Data view plus BE32+24, rawLE32+28/+32; then LE32 length/data via readDataBuffer/writeDataBuffer | Extra fields mutate before allocation/data failure; base generic wire methods differ from derived chunk wire |
| FileDataEvent 17988 | Separate fixed4096 storage, id lowLE16/full32 storage,2rawLE32,2LE16; cap-copy/skip | Independently closed; does not use Core::IO::Buffer; original pool creation still pending |

## Failure and lifetime obligations

- ARM app item observations place buffer storage at item+16 and event storage
  at item+32. This is a binary-analysis observation, not a native class layout.
- `read` calls virtual item data access and common-header read, then reads a
  raw LE32 length. Allocation occurs before verifying the remaining payload.
  If resize succeeds, the event view pointer/declared length change even when
  the subsequent payload read fails. If resize fails, the prior view remains.
- `create(Event const&)` calls virtual no-argument allocation, copies event
  fields, ignores resize's result, conditionally calls copyFrom only when the
  raw length interpreted as signed32 is positive, ignores copied-byte count,
  then assigns view pointer from buffer and retains the source declared length.
  Failed allocation can therefore return an item whose declared view length
  exceeds its null/short actual storage. Tests must preserve this distinction.
- Actual Core `copyFrom` copies min(storage-size,source-size); it does not
  resize. Actual Buffer has implicit memberwise copy: owning copies are unsafe.
  `take` overwrites destination without first freeing it, so candidates avoid it.
- Original no-argument class creation, pools, refcount/base fields, original
  DataItem/PooledDataItem destructors and constructor/vtable ABI remain pending.
  Independent allocation/binding helpers are not recovered original methods.
- Null+zero libc avoidance retains sealed buffer position/capacity validation;
  only defined-state equivalence is claimed. No real4GiB allocator requests,
  invalid memcpy ranges, unsafe oversized views or device programming execute.

Exact mangles, declarations, addresses, sizes, source ELF identities and source
file hashes are preserved in `dependency-graph.json`. Candidate declarations
will use real Core headers; they remain outside installed/source build trees
until the actual provider and behavioral proofs are ready.
'''
 (target/'DEPENDENCIES.md').write_text(text);print('Mapped variable-data declarations, real Core API and ownership/failure boundaries')

if __name__=='__main__':main()
