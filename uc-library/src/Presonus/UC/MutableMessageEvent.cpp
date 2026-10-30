#include "core/portable/corepersistence.h"
#include "core/portable/corezipstream.h"
#include "core/public/corememstream.h"
#include "presonus/uc/message_attributes.hpp"
#include "presonus/uc/mutable_message_event.hpp"
#include <cstdint>

namespace Presonus::UC {
namespace {
auto word(const unsigned char *bytes) {
  return std::uint32_t(bytes[0]) | (std::uint32_t(bytes[1]) << 8) |
         (std::uint32_t(bytes[2]) << 16) | (std::uint32_t(bytes[3]) << 24);
}
auto compressed(int type) { return type == 0x5a42 || type == 0x5a4d; }
} // namespace
MutableMessageEvent::MutableMessageEvent()
    : event_{{0x4a4d, 24, 0, 0}, nullptr, 0}, buffer_(nullptr, 0, true) {}
MutableMessageEvent::MutableMessageEvent(const MessageAttributes &attributes,
                                         int type, int allocationHint)
    : MutableMessageEvent() {
  assign(attributes, type, allocationHint);
}
MutableMessageEvent &
MutableMessageEvent::assign(const MessageAttributes &attributes, int type,
                            int allocationHint) {
  const auto opaque =
      presonus::uc::MessageAttributesPortAccess::opaqueState(attributes);
  event_.header.routeA = word(opaque.data());
  event_.header.routeB = word(opaque.data() + 4);
  event_.header.type = static_cast<std::uint32_t>(type);
  Core::IO::MemoryStream stream(8192);
  if (allocationHint > 0)
    stream.allocateMemory(static_cast<std::uint32_t>(allocationHint), false);
  const auto format = type == 0x5a42 || type == 0x5542
                          ? Core::Portable::Archiver::kUBJSON
                          : Core::Portable::Archiver::kJSON;
  Core::Portable::Archiver archive(&stream, format, 1);
  archive.save(attributes);
  takeData(stream, compressed(type));
  return *this;
}
MutableMessageEvent &MutableMessageEvent::assign(Core::IO::MemoryStream &stream,
                                                 int type) {
  event_.header.routeA = 0;
  event_.header.routeB = 0;
  event_.header.type = static_cast<std::uint32_t>(type);
  takeData(stream, compressed(type));
  return *this;
}
void MutableMessageEvent::takeData(Core::IO::MemoryStream &stream,
                                   bool compress) {
  buffer_.resize(0);
  if (compress) {
    Core::IO::MemoryStream zipped(16384);
    const auto *source = stream.getBuffer().getAddress();
    const auto count = stream.getBytesWritten();
    Core::Portable::ThreadAwareCompression::zip(zipped, source,
                                                static_cast<int>(count), 15);
    // getBuffer exposes const even on a genuine nonconst MemoryStream. Transfer
    // mutates only that actual internal Buffer, matching original donor take.
    buffer_.take(const_cast<Core::IO::Buffer &>(zipped.getBuffer()));
    event_.sizeBits = zipped.getBytesWritten();
  } else {
    buffer_.take(const_cast<Core::IO::Buffer &>(stream.getBuffer()));
    event_.sizeBits = stream.getBytesWritten();
  }
  event_.data = buffer_.getAddress();
}
} // namespace Presonus::UC
