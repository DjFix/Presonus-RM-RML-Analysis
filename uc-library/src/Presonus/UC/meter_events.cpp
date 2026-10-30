#include "presonus/uc/meter_events.hpp"
#include <algorithm>
namespace {
bool writeBE32(Presonus::UC::BufferWriter &writer, std::uint32_t value) {
  const unsigned char bytes[4] = {static_cast<unsigned char>(value >> 24),
                                  static_cast<unsigned char>(value >> 16),
                                  static_cast<unsigned char>(value >> 8),
                                  static_cast<unsigned char>(value)};
  return writer.writeRaw(bytes, 4);
}
bool readBE32(Presonus::UC::BufferReader &reader, std::uint32_t &value) {
  unsigned char bytes[4]{};
  if (!reader.readRaw(bytes, 4))
    return false;
  value = (std::uint32_t(bytes[0]) << 24) | (std::uint32_t(bytes[1]) << 16) |
          (std::uint32_t(bytes[2]) << 8) | std::uint32_t(bytes[3]);
  return true;
}
} // namespace
namespace Presonus::UC {
template <class T, int Type>
bool MeterEventClass<T, Type>::write(BufferWriter &writer,
                                     const T &event) const {
  writeBE32(writer, event.keyBits);
  writer.write<unsigned short>(event.source);
  writer.write<unsigned short>(event.count);
  if (!writer.writeRaw(event.data.data(), int(event.count) * T::sampleWidth))
    return false;
  writer.writeRaw(&event.recordCount, 1);
  for (unsigned i = 0; i < event.recordCount; ++i) {
    writer.write<unsigned short>(event.records[i].a);
    writer.write<unsigned short>(event.records[i].b);
    writer.write<unsigned short>(event.records[i].c);
  }
  return true;
}
template <class T, int Type>
bool MeterEventClass<T, Type>::read(T &event, BufferReader &reader) const {
  readBE32(reader, event.keyBits);
  reader.read<unsigned short>(event.source);
  reader.read<unsigned short>(event.count);
  if (!reader.readRaw(event.data.data(), int(event.count) * T::sampleWidth,
                      int(event.data.size())))
    return false;
  reader.readRaw(&event.recordCount, 1);
  event.recordCount = std::min<unsigned char>(event.recordCount, 36);
  for (unsigned i = 0; i < event.recordCount; ++i) {
    if (reader.read<unsigned short>(event.records[i].a))
      if (reader.read<unsigned short>(event.records[i].b))
        reader.read<unsigned short>(event.records[i].c);
  }
  return true;
}
template class MeterEventClass<MeterEvent8, 19778>;
template class MeterEventClass<MeterEvent16, 19795>;
template <>
bool PrimitiveEventClass<MeterEvent8, 19778>::write(BufferWriter &writer,
                                                    const Event &event) const {
  if (!EventClass().write(writer, event))
    return false;
  return callbacks_.write(callbacks_.context, writer, event);
}
template <>
bool PrimitiveEventClass<MeterEvent8, 19778>::read(Event &event,
                                                   BufferReader &reader) const {
  if (!EventClass().read(event, reader))
    return false;
  return callbacks_.read(callbacks_.context, event, reader);
}
template <>
bool PrimitiveEventClass<MeterEvent16, 19795>::write(BufferWriter &writer,
                                                     const Event &event) const {
  if (!EventClass().write(writer, event))
    return false;
  return callbacks_.write(callbacks_.context, writer, event);
}
template <>
bool PrimitiveEventClass<MeterEvent16, 19795>::read(
    Event &event, BufferReader &reader) const {
  if (!EventClass().read(event, reader))
    return false;
  return callbacks_.read(callbacks_.context, event, reader);
}
} // namespace Presonus::UC
