#pragma once
#include "presonus/uc/typed_factory_codec.hpp"
namespace Presonus::UC {
// Portable storage, not original field names/semantic types, inheritance,
// ownership, constructors or layout/vtable/ARM ABI. Raw numeric bytes remain
// opaque; no float, timestamp, MIDI content or UTF-8 normalization is applied.
struct TimeCodeRecord {
  unsigned char a = 0, b = 0;
  std::array<unsigned char, 6> reserved{};
  std::array<unsigned char, 8> rawBytes{};
};
struct TimeCodeEvent {
  Event header;
  std::uint32_t keyBits = 0;
  unsigned char recordCount = 0;
  std::array<unsigned char, 3> reserved15{};
  std::array<TimeCodeRecord, 4> records{};
};
struct MusicInputEvent {
  Event header;
  std::uint32_t idBits = 0;
  unsigned char modeByte = 0;
  std::array<unsigned char, 3> reserved15{};
  std::uint32_t valueBits = 0;
};
struct DebugEvent {
  Event header;
  std::array<char, 1024> text{};
};
struct MidiShortSysexEvent {
  Event header;
  unsigned short count = 0;
  std::array<unsigned char, 512> data{};
};
// Timecode ignores header/record transfer failures and returns1. Reader clamps
// retained/read count to4 without skipping extra records. Writer count MUST be
// <=4: original loads outside its bounded record array for larger counts.
class TimeCodeEventClass {
public:
  bool write(BufferWriter &, const TimeCodeEvent &) const;
  bool read(TimeCodeEvent &, BufferReader &) const;
};
// MusicInput lowBE16 ID zero-extends on success, stays unchanged on a short
// first read; then a byte and rawLE32. Subsequent failures retain prior fields.
class MusicInputEventClass {
public:
  bool write(BufferWriter &, const MusicInputEvent &) const;
  bool read(MusicInputEvent &, BufferReader &) const;
};
class DebugEventClass {
public:
  bool write(BufferWriter &, const DebugEvent &) const;
  bool read(DebugEvent &, BufferReader &) const;
};
// LE16 count followed by bytes. Reader copiesmin(count,512), then skips excess
// retaining full count; failed skip retains copied bytes/cursor. Writer has no
// clamp: count>512 is valid only if rejected for insufficient capacity before
// data access. Successful oversized original copies are unsafe and excluded.
class MidiShortSysexEventClass {
public:
  bool write(BufferWriter &, const MidiShortSysexEvent &) const;
  bool read(MidiShortSysexEvent &, BufferReader &) const;
};
// All original non-template return spellings are unencoded; portable bool
// declarations match observed ARM0/1 results. Payloads omit the common header.
template <>
bool PrimitiveEventClass<TimeCodeEvent, 21571>::write(BufferWriter &,
                                                      const Event &) const;
template <>
bool PrimitiveEventClass<TimeCodeEvent, 21571>::read(Event &,
                                                     BufferReader &) const;
template <>
bool PrimitiveEventClass<MusicInputEvent, 19785>::write(BufferWriter &,
                                                        const Event &) const;
template <>
bool PrimitiveEventClass<MusicInputEvent, 19785>::read(Event &,
                                                       BufferReader &) const;
template <>
bool PrimitiveEventClass<DebugEvent, 17474>::write(BufferWriter &,
                                                   const Event &) const;
template <>
bool PrimitiveEventClass<DebugEvent, 17474>::read(Event &,
                                                  BufferReader &) const;
template <>
bool PrimitiveEventClass<MidiShortSysexEvent, 21331>::write(
    BufferWriter &, const Event &) const;
template <>
bool PrimitiveEventClass<MidiShortSysexEvent, 21331>::read(
    Event &, BufferReader &) const;
} // namespace Presonus::UC
namespace presonus::uc {
using TimeCodeFactoryCodec =
    TypedFactoryCodec<Presonus::UC::TimeCodeEvent,
                      Presonus::UC::TimeCodeEventClass, 21571>;
using MusicInputFactoryCodec =
    TypedFactoryCodec<Presonus::UC::MusicInputEvent,
                      Presonus::UC::MusicInputEventClass, 19785>;
using DebugFactoryCodec =
    TypedFactoryCodec<Presonus::UC::DebugEvent, Presonus::UC::DebugEventClass,
                      17474>;
using MidiShortSysexFactoryCodec =
    TypedFactoryCodec<Presonus::UC::MidiShortSysexEvent,
                      Presonus::UC::MidiShortSysexEventClass, 21331>;
} // namespace presonus::uc
