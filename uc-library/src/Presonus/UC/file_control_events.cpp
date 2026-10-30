#include "presonus/uc/file_control_events.hpp"
namespace {
bool readId(std::uint32_t &bits, Presonus::UC::BufferReader &reader) {
  unsigned short value = 0;
  bool result = reader.read<unsigned short>(value);
  bits = value;
  return result;
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
} // namespace
namespace Presonus::UC {
bool FileRequestEventClass::write(BufferWriter &writer,
                                  const FileRequestEvent &event) const {
  if (!writer.write<unsigned short>(static_cast<unsigned short>(event.idBits)))
    return false;
  if (!writeBE32(writer, event.requestBits))
    return false;
  for (const auto &text : event.strings)
    if (!writer.writeCString(text.data()))
      return false;
  return true;
}
bool FileRequestEventClass::read(FileRequestEvent &event,
                                 BufferReader &reader) const {
  if (!readId(event.idBits, reader))
    return false;
  if (!readBE32(event.requestBits, reader))
    return false;
  for (auto &text : event.strings)
    if (!reader.readCString(text.data(), 256))
      return false;
  return true;
}
bool FileDataRateEventClass::write(BufferWriter &writer,
                                   const FileDataRateEvent &event) const {
  if (!writer.write<unsigned short>(static_cast<unsigned short>(event.idBits)))
    return false;
  for (auto bits : event.wordBits)
    if (!writeLE32(writer, bits))
      return false;
  return true;
}
bool FileDataRateEventClass::read(FileDataRateEvent &event,
                                  BufferReader &reader) const {
  if (!readId(event.idBits, reader))
    return false;
  for (auto &bits : event.wordBits)
    if (!readLE32(bits, reader))
      return false;
  return true;
}
bool FileAbortEventClass::write(BufferWriter &writer,
                                const FileAbortEvent &event) const {
  return writer.write<unsigned short>(
      static_cast<unsigned short>(event.idBits));
}
bool FileAbortEventClass::read(FileAbortEvent &event,
                               BufferReader &reader) const {
  return readId(event.idBits, reader);
}
template <>
bool PrimitiveEventClass<FileRequestEvent, 18002>::write(
    BufferWriter &writer, const Event &event) const {
  if (!EventClass().write(writer, event))
    return false;
  return callbacks_.write(callbacks_.context, writer, event);
}
template <>
bool PrimitiveEventClass<FileRequestEvent, 18002>::read(
    Event &event, BufferReader &reader) const {
  if (!EventClass().read(event, reader))
    return false;
  return callbacks_.read(callbacks_.context, event, reader);
}
template <>
bool PrimitiveEventClass<FileDataRateEvent, 18003>::write(
    BufferWriter &writer, const Event &event) const {
  if (!EventClass().write(writer, event))
    return false;
  return callbacks_.write(callbacks_.context, writer, event);
}
template <>
bool PrimitiveEventClass<FileDataRateEvent, 18003>::read(
    Event &event, BufferReader &reader) const {
  if (!EventClass().read(event, reader))
    return false;
  return callbacks_.read(callbacks_.context, event, reader);
}
template <>
bool PrimitiveEventClass<FileAbortEvent, 17985>::write(
    BufferWriter &writer, const Event &event) const {
  if (!EventClass().write(writer, event))
    return false;
  return callbacks_.write(callbacks_.context, writer, event);
}
template <>
bool PrimitiveEventClass<FileAbortEvent, 17985>::read(
    Event &event, BufferReader &reader) const {
  if (!EventClass().read(event, reader))
    return false;
  return callbacks_.read(callbacks_.context, event, reader);
}
} // namespace Presonus::UC
