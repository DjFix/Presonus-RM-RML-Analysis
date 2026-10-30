#include "presonus/uc/misc_events.hpp"
#include <algorithm>
namespace {
bool writeBE32(Presonus::UC::BufferWriter &writer, std::uint32_t value) {
  const unsigned char bytes[4] = {static_cast<unsigned char>(value >> 24),
                                  static_cast<unsigned char>(value >> 16),
                                  static_cast<unsigned char>(value >> 8),
                                  static_cast<unsigned char>(value)};
  return writer.writeRaw(bytes, 4);
}
bool readBE32(std::uint32_t &value, Presonus::UC::BufferReader &reader) {
  unsigned char bytes[4]{};
  if (!reader.readRaw(bytes, 4))
    return false;
  value = (std::uint32_t(bytes[0]) << 24) | (std::uint32_t(bytes[1]) << 16) |
          (std::uint32_t(bytes[2]) << 8) | std::uint32_t(bytes[3]);
  return true;
}
bool writeLE32(Presonus::UC::BufferWriter &writer, std::uint32_t value) {
  const unsigned char bytes[4] = {static_cast<unsigned char>(value),
                                  static_cast<unsigned char>(value >> 8),
                                  static_cast<unsigned char>(value >> 16),
                                  static_cast<unsigned char>(value >> 24)};
  return writer.writeRaw(bytes, 4);
}
bool readLE32(std::uint32_t &value, Presonus::UC::BufferReader &reader) {
  unsigned char bytes[4]{};
  if (!reader.readRaw(bytes, 4))
    return false;
  value = std::uint32_t(bytes[0]) | (std::uint32_t(bytes[1]) << 8) |
          (std::uint32_t(bytes[2]) << 16) | (std::uint32_t(bytes[3]) << 24);
  return true;
}
} // namespace
namespace Presonus::UC {
bool TimeCodeEventClass::write(BufferWriter &writer,
                               const TimeCodeEvent &event) const {
  writeBE32(writer, event.keyBits);
  writer.writeRaw(&event.recordCount, 1);
  for (unsigned i = 0; i < event.recordCount; ++i) {
    writer.writeRaw(&event.records[i].a, 1);
    writer.writeRaw(&event.records[i].b, 1);
    writer.writeRaw(event.records[i].rawBytes.data(), 8);
  }
  return true;
}
bool TimeCodeEventClass::read(TimeCodeEvent &event,
                              BufferReader &reader) const {
  readBE32(event.keyBits, reader);
  reader.readRaw(&event.recordCount, 1);
  event.recordCount = std::min<unsigned char>(event.recordCount, 4);
  for (unsigned i = 0; i < event.recordCount; ++i) {
    reader.readRaw(&event.records[i].a, 1);
    reader.readRaw(&event.records[i].b, 1);
    reader.readRaw(event.records[i].rawBytes.data(), 8);
  }
  return true;
}
bool MusicInputEventClass::write(BufferWriter &writer,
                                 const MusicInputEvent &event) const {
  const unsigned char id[2] = {static_cast<unsigned char>(event.idBits >> 8),
                               static_cast<unsigned char>(event.idBits)};
  return writer.writeRaw(id, 2) && writer.writeRaw(&event.modeByte, 1) &&
         writeLE32(writer, event.valueBits);
}
bool MusicInputEventClass::read(MusicInputEvent &event,
                                BufferReader &reader) const {
  unsigned char id[2]{};
  if (!reader.readRaw(id, 2))
    return false;
  event.idBits = (std::uint32_t(id[0]) << 8) | std::uint32_t(id[1]);
  return reader.readRaw(&event.modeByte, 1) &&
         readLE32(event.valueBits, reader);
}
bool DebugEventClass::write(BufferWriter &writer,
                            const DebugEvent &event) const {
  return writer.writeCString(event.text.data());
}
bool DebugEventClass::read(DebugEvent &event, BufferReader &reader) const {
  return reader.readCString(event.text.data(), 1024);
}
bool MidiShortSysexEventClass::write(BufferWriter &writer,
                                     const MidiShortSysexEvent &event) const {
  return writer.write<unsigned short>(event.count) &&
         writer.writeRaw(event.data.data(), event.count);
}
bool MidiShortSysexEventClass::read(MidiShortSysexEvent &event,
                                    BufferReader &reader) const {
  return reader.read<unsigned short>(event.count) &&
         reader.readRaw(event.data.data(), event.count, int(event.data.size()));
}
template <>
bool PrimitiveEventClass<TimeCodeEvent, 21571>::write(
    BufferWriter &writer, const Event &event) const {
  if (!EventClass().write(writer, event))
    return false;
  return callbacks_.write(callbacks_.context, writer, event);
}
template <>
bool PrimitiveEventClass<TimeCodeEvent, 21571>::read(
    Event &event, BufferReader &reader) const {
  if (!EventClass().read(event, reader))
    return false;
  return callbacks_.read(callbacks_.context, event, reader);
}
template <>
bool PrimitiveEventClass<MusicInputEvent, 19785>::write(
    BufferWriter &writer, const Event &event) const {
  if (!EventClass().write(writer, event))
    return false;
  return callbacks_.write(callbacks_.context, writer, event);
}
template <>
bool PrimitiveEventClass<MusicInputEvent, 19785>::read(
    Event &event, BufferReader &reader) const {
  if (!EventClass().read(event, reader))
    return false;
  return callbacks_.read(callbacks_.context, event, reader);
}
template <>
bool PrimitiveEventClass<DebugEvent, 17474>::write(BufferWriter &writer,
                                                   const Event &event) const {
  if (!EventClass().write(writer, event))
    return false;
  return callbacks_.write(callbacks_.context, writer, event);
}
template <>
bool PrimitiveEventClass<DebugEvent, 17474>::read(Event &event,
                                                  BufferReader &reader) const {
  if (!EventClass().read(event, reader))
    return false;
  return callbacks_.read(callbacks_.context, event, reader);
}
template <>
bool PrimitiveEventClass<MidiShortSysexEvent, 21331>::write(
    BufferWriter &writer, const Event &event) const {
  if (!EventClass().write(writer, event))
    return false;
  return callbacks_.write(callbacks_.context, writer, event);
}
template <>
bool PrimitiveEventClass<MidiShortSysexEvent, 21331>::read(
    Event &event, BufferReader &reader) const {
  if (!EventClass().read(event, reader))
    return false;
  return callbacks_.read(callbacks_.context, event, reader);
}
} // namespace Presonus::UC
