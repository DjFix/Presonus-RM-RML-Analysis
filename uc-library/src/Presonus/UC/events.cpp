#include "presonus/uc/events.hpp"

namespace Presonus::UC {
bool EventClass::write(BufferWriter &writer, const Event &event) const {
  const unsigned char tag[2] = {static_cast<unsigned char>(event.type >> 8),
                                static_cast<unsigned char>(event.type)};
  if (!writer.writeRaw(tag, 2))
    return false;
  if (!writer.write<unsigned short>(static_cast<unsigned short>(event.routeA)))
    return false;
  return writer.write<unsigned short>(
      static_cast<unsigned short>(event.routeB));
}

bool EventClass::read(Event &event, BufferReader &reader) const {
  unsigned short route = 0;
  if (!reader.read<unsigned short>(route)) {
    event.routeA = 0;
    return false;
  }
  event.routeA = route;
  route = 0;
  if (!reader.read<unsigned short>(route)) {
    event.routeB = 0;
    return false;
  }
  event.routeB = route;
  return true;
}

bool ParamValueEventClass::write(BufferWriter &writer,
                                 const ParamValueEvent &event) const {
  if (!writer.writeCString(event.path.data()))
    return false;
  if (!writer.write<unsigned short>(event.index))
    return false;
  const unsigned char value[4] = {
      static_cast<unsigned char>(event.valueBits),
      static_cast<unsigned char>(event.valueBits >> 8),
      static_cast<unsigned char>(event.valueBits >> 16),
      static_cast<unsigned char>(event.valueBits >> 24)};
  return writer.writeRaw(value, 4);
}

bool ParamValueEventClass::read(ParamValueEvent &event,
                                BufferReader &reader) const {
  if (!reader.readCString(event.path.data(), 128))
    return false;
  if (!reader.read<unsigned short>(event.index))
    return false;
  unsigned char value[4]{};
  if (!reader.readRaw(value, 4))
    return false;
  event.valueBits = std::uint32_t(value[0]) | (std::uint32_t(value[1]) << 8) |
                    (std::uint32_t(value[2]) << 16) |
                    (std::uint32_t(value[3]) << 24);
  return true;
}

bool ParamStringEventClass::write(BufferWriter &writer,
                                  const ParamStringEvent &event) const {
  if (!writer.writeCString(event.path.data()))
    return false;
  if (!writer.write<unsigned short>(event.index))
    return false;
  return writer.writeCString(event.text.data());
}

bool ParamStringEventClass::read(ParamStringEvent &event,
                                 BufferReader &reader) const {
  if (!reader.readCString(event.path.data(), 128))
    return false;
  if (!reader.read<unsigned short>(event.index))
    return false;
  return reader.readCString(event.text.data(), 256);
}
} // namespace Presonus::UC
