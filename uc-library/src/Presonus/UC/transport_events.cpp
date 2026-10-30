#include "presonus/uc/transport_events.hpp"

namespace Presonus::UC {
bool UDPMappingEventClass::read(UDPMappingEvent &event,
                                BufferReader &reader) const {
  return reader.read<unsigned short>(event.mapping);
}
bool UDPMappingEventClass::write(BufferWriter &writer,
                                 const UDPMappingEvent &event) const {
  return writer.write<unsigned short>(event.mapping);
}
bool MidiMessageEventClass::read(MidiMessageEvent &event,
                                 BufferReader &reader) const {
  return reader.readRaw(event.bytes.data(), 4);
}
bool MidiMessageEventClass::write(BufferWriter &writer,
                                  const MidiMessageEvent &event) const {
  return writer.writeRaw(event.bytes.data(), 4);
}
bool ExtensionQueryEventClass::read(ExtensionQueryEvent &event,
                                    BufferReader &reader) const {
  unsigned char bytes[4]{};
  if (!reader.readRaw(bytes, 4))
    return false;
  event.query = (std::uint32_t(bytes[0]) << 24) |
                (std::uint32_t(bytes[1]) << 16) |
                (std::uint32_t(bytes[2]) << 8) | std::uint32_t(bytes[3]);
  return true;
}
bool ExtensionQueryEventClass::write(BufferWriter &writer,
                                     const ExtensionQueryEvent &event) const {
  const unsigned char bytes[4] = {static_cast<unsigned char>(event.query >> 24),
                                  static_cast<unsigned char>(event.query >> 16),
                                  static_cast<unsigned char>(event.query >> 8),
                                  static_cast<unsigned char>(event.query)};
  return writer.writeRaw(bytes, 4);
}
} // namespace Presonus::UC
