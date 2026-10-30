#pragma once
#include "presonus/uc/events.hpp"

namespace Presonus::UC {
// Portable storage only: original inheritance/layout/vtables and field names
// are not recovered. The ARM payload begins at byte +16 of each event image.
struct UDPMappingEvent {
  Event header;
  unsigned short mapping = 0;
};
struct MidiMessageEvent {
  Event header;
  std::array<unsigned char, 4> bytes{};
};
struct ExtensionQueryEvent {
  Event header;
  std::uint32_t query = 0;
};

// Typed payload codecs; common header/tag processing is a separate stage.
// Non-template bool spelling is unencoded; observed ARM returns are 0/1.
// Insufficient capacity leaves cursor, event and output unchanged.
class UDPMappingEventClass {
public:
  bool read(UDPMappingEvent &event, BufferReader &reader) const;
  bool write(BufferWriter &writer, const UDPMappingEvent &event) const;
};
class MidiMessageEventClass {
public:
  bool read(MidiMessageEvent &event, BufferReader &reader) const;
  bool write(BufferWriter &writer, const MidiMessageEvent &event) const;
};
class ExtensionQueryEventClass {
public:
  bool read(ExtensionQueryEvent &event, BufferReader &reader) const;
  bool write(BufferWriter &writer, const ExtensionQueryEvent &event) const;
};
} // namespace Presonus::UC
