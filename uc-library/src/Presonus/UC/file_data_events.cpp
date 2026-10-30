#include "presonus/uc/file_data_events.hpp"
namespace {
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
bool FileDataEventClass::write(BufferWriter &writer,
                               const FileDataEvent &event) const {
  if (!writer.write<unsigned short>(static_cast<unsigned short>(event.idBits)))
    return false;
  for (auto word : event.wordBits)
    if (!writeLE32(writer, word))
      return false;
  return writer.write<unsigned short>(event.partBits) &&
         writer.write<unsigned short>(event.count) &&
         writer.writeRaw(event.data.data(), event.count);
}
bool FileDataEventClass::read(FileDataEvent &event,
                              BufferReader &reader) const {
  unsigned short id = 0;
  bool result = reader.read<unsigned short>(id);
  event.idBits = id;
  if (!result)
    return false;
  for (auto &word : event.wordBits)
    if (!readLE32(word, reader))
      return false;
  return reader.read<unsigned short>(event.partBits) &&
         reader.read<unsigned short>(event.count) &&
         reader.readRaw(event.data.data(), event.count, int(event.data.size()));
}
template <>
bool PrimitiveEventClass<FileDataEvent, 17988>::write(
    BufferWriter &writer, const Event &event) const {
  if (!EventClass().write(writer, event))
    return false;
  return callbacks_.write(callbacks_.context, writer, event);
}
template <>
bool PrimitiveEventClass<FileDataEvent, 17988>::read(
    Event &event, BufferReader &reader) const {
  if (!EventClass().read(event, reader))
    return false;
  return callbacks_.read(callbacks_.context, event, reader);
}
} // namespace Presonus::UC
