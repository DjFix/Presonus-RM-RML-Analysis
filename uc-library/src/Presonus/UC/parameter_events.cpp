#include "presonus/uc/parameter_events.hpp"
namespace {
template <class T>
bool writePrefix(Presonus::UC::BufferWriter &writer, const T &event) {
  return writer.writeCString(event.path.data()) &&
         writer.write<unsigned short>(event.index);
}
template <class T>
bool readPrefix(T &event, Presonus::UC::BufferReader &reader) {
  return reader.readCString(event.path.data(), 128) &&
         reader.read<unsigned short>(event.index);
}
bool writeBits(Presonus::UC::BufferWriter &writer, std::uint32_t bits) {
  const unsigned char bytes[4] = {static_cast<unsigned char>(bits),
                                  static_cast<unsigned char>(bits >> 8),
                                  static_cast<unsigned char>(bits >> 16),
                                  static_cast<unsigned char>(bits >> 24)};
  return writer.writeRaw(bytes, 4);
}
bool readBits(std::uint32_t &bits, Presonus::UC::BufferReader &reader) {
  unsigned char bytes[4]{};
  if (!reader.readRaw(bytes, 4))
    return false;
  bits = std::uint32_t(bytes[0]) | (std::uint32_t(bytes[1]) << 8) |
         (std::uint32_t(bytes[2]) << 16) | (std::uint32_t(bytes[3]) << 24);
  return true;
}
} // namespace
namespace Presonus::UC {
bool ParamEditEventClass::write(BufferWriter &writer,
                                const ParamEditEvent &event) const {
  return writePrefix(writer, event);
}
bool ParamEditEventClass::read(ParamEditEvent &event,
                               BufferReader &reader) const {
  return readPrefix(event, reader);
}
bool ParamModeEventClass::write(BufferWriter &writer,
                                const ParamModeEvent &event) const {
  return writePrefix(writer, event) &&
         writer.writeCString(event.modeBytes.data());
}
bool ParamModeEventClass::read(ParamModeEvent &event,
                               BufferReader &reader) const {
  return readPrefix(event, reader) &&
         reader.readCString(event.modeBytes.data(), 64);
}
bool ParamIncrementEventClass::write(BufferWriter &writer,
                                     const ParamIncrementEvent &event) const {
  return writePrefix(writer, event) &&
         writer.write<unsigned short>(event.incrementBits);
}
bool ParamIncrementEventClass::read(ParamIncrementEvent &event,
                                    BufferReader &reader) const {
  return readPrefix(event, reader) &&
         reader.read<unsigned short>(event.incrementBits);
}
bool ParamColorEventClass::write(BufferWriter &writer,
                                 const ParamColorEvent &event) const {
  return writePrefix(writer, event) && writeBits(writer, event.colorBits);
}
bool ParamColorEventClass::read(ParamColorEvent &event,
                                BufferReader &reader) const {
  return readPrefix(event, reader) && readBits(event.colorBits, reader);
}
bool ParamRangeEventClass::write(BufferWriter &writer,
                                 const ParamRangeEvent &event) const {
  if (!writePrefix(writer, event))
    return false;
  for (auto bits : event.wordBits)
    if (!writeBits(writer, bits))
      return false;
  for (const auto &label : event.labels)
    if (!writer.writeCString(label.data()))
      return false;
  return true;
}
bool ParamRangeEventClass::read(ParamRangeEvent &event,
                                BufferReader &reader) const {
  if (!readPrefix(event, reader))
    return false;
  for (auto &bits : event.wordBits)
    if (!readBits(bits, reader))
      return false;
  for (auto &label : event.labels)
    if (!reader.readCString(label.data(), 32))
      return false;
  return true;
}
bool ParamStringListEventClass::write(BufferWriter &writer,
                                      const ParamStringListEvent &event) const {
  return writePrefix(writer, event) && writeBits(writer, event.listFieldBits) &&
         writer.writeCString(event.text.data());
}
bool ParamStringListEventClass::read(ParamStringListEvent &event,
                                     BufferReader &reader) const {
  return readPrefix(event, reader) && readBits(event.listFieldBits, reader) &&
         reader.readCString(event.text.data(), 1024);
}
template <>
bool PrimitiveEventClass<ParamEditEvent, 20549>::write(
    BufferWriter &writer, const Event &event) const {
  if (!EventClass().write(writer, event))
    return false;
  return callbacks_.write(callbacks_.context, writer, event);
}
template <>
bool PrimitiveEventClass<ParamEditEvent, 20549>::read(
    Event &event, BufferReader &reader) const {
  if (!EventClass().read(event, reader))
    return false;
  return callbacks_.read(callbacks_.context, event, reader);
}
template <>
bool PrimitiveEventClass<ParamModeEvent, 20557>::write(
    BufferWriter &writer, const Event &event) const {
  if (!EventClass().write(writer, event))
    return false;
  return callbacks_.write(callbacks_.context, writer, event);
}
template <>
bool PrimitiveEventClass<ParamModeEvent, 20557>::read(
    Event &event, BufferReader &reader) const {
  if (!EventClass().read(event, reader))
    return false;
  return callbacks_.read(callbacks_.context, event, reader);
}
template <>
bool PrimitiveEventClass<ParamIncrementEvent, 20553>::write(
    BufferWriter &writer, const Event &event) const {
  if (!EventClass().write(writer, event))
    return false;
  return callbacks_.write(callbacks_.context, writer, event);
}
template <>
bool PrimitiveEventClass<ParamIncrementEvent, 20553>::read(
    Event &event, BufferReader &reader) const {
  if (!EventClass().read(event, reader))
    return false;
  return callbacks_.read(callbacks_.context, event, reader);
}
template <>
bool PrimitiveEventClass<ParamColorEvent, 20547>::write(
    BufferWriter &writer, const Event &event) const {
  if (!EventClass().write(writer, event))
    return false;
  return callbacks_.write(callbacks_.context, writer, event);
}
template <>
bool PrimitiveEventClass<ParamColorEvent, 20547>::read(
    Event &event, BufferReader &reader) const {
  if (!EventClass().read(event, reader))
    return false;
  return callbacks_.read(callbacks_.context, event, reader);
}
template <>
bool PrimitiveEventClass<ParamRangeEvent, 20562>::write(
    BufferWriter &writer, const Event &event) const {
  if (!EventClass().write(writer, event))
    return false;
  return callbacks_.write(callbacks_.context, writer, event);
}
template <>
bool PrimitiveEventClass<ParamRangeEvent, 20562>::read(
    Event &event, BufferReader &reader) const {
  if (!EventClass().read(event, reader))
    return false;
  return callbacks_.read(callbacks_.context, event, reader);
}
template <>
bool PrimitiveEventClass<ParamStringListEvent, 20556>::write(
    BufferWriter &writer, const Event &event) const {
  if (!EventClass().write(writer, event))
    return false;
  return callbacks_.write(callbacks_.context, writer, event);
}
template <>
bool PrimitiveEventClass<ParamStringListEvent, 20556>::read(
    Event &event, BufferReader &reader) const {
  if (!EventClass().read(event, reader))
    return false;
  return callbacks_.read(callbacks_.context, event, reader);
}
} // namespace Presonus::UC
