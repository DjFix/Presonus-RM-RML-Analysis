#include "presonus/uc/discovery_events.hpp"
namespace {
bool write32(Presonus::UC::BufferWriter &writer, std::uint32_t value) {
  const unsigned char bytes[4] = {static_cast<unsigned char>(value),
                                  static_cast<unsigned char>(value >> 8),
                                  static_cast<unsigned char>(value >> 16),
                                  static_cast<unsigned char>(value >> 24)};
  return writer.writeRaw(bytes, 4);
}
bool read32(Presonus::UC::BufferReader &reader, std::uint32_t &value) {
  unsigned char bytes[4]{};
  if (!reader.readRaw(bytes, 4))
    return false;
  value = std::uint32_t(bytes[0]) | (std::uint32_t(bytes[1]) << 8) |
          (std::uint32_t(bytes[2]) << 16) | (std::uint32_t(bytes[3]) << 24);
  return true;
}
} // namespace
namespace Presonus::UC {
bool DiscoveryAliveEventClass::write(BufferWriter &writer,
                                     const DiscoveryAliveEvent &event) const {
  // Original intentionally ignores this result and several extension failures.
  write32(writer, event.versionBits);
  if (event.versionBits & 0x80000000U) {
    if (write32(writer, event.extensionBits))
      if (writer.write<unsigned short>(event.extensionA))
        if (writer.write<unsigned short>(event.extensionB))
          writer.writeRaw(event.extensionBytes.data(), 8);
  }
  for (const auto &text : event.strings)
    if (!writer.writeCString(text.data()))
      return false;
  return true;
}
bool DiscoveryAliveEventClass::read(DiscoveryAliveEvent &event,
                                    BufferReader &reader) const {
  // If the initial word cannot be read, the retained version controls decoding.
  read32(reader, event.versionBits);
  if (event.versionBits & 0x80000000U) {
    if (!read32(reader, event.extensionBits))
      return false;
    if (!reader.read<unsigned short>(event.extensionA))
      return false;
    if (!reader.read<unsigned short>(event.extensionB))
      return false;
    if (!reader.readRaw(event.extensionBytes.data(), 8))
      return false;
  }
  for (auto &text : event.strings)
    if (!reader.readCString(text.data(), 64))
      return false;
  return true;
}
} // namespace Presonus::UC
