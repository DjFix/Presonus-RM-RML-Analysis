#include "core/portable/corepersistence.h"
#include "core/portable/corezipstream.h"
#include "core/public/corememstream.h"
#include "presonus/uc/message_attributes.hpp"
#include "presonus/uc/network_manager_services.hpp"

namespace Presonus::UC {
MessageAttributes::MessageAttributes(const MessageEvent &event)
    : Core::Portable::Attributes(
          Core::Portable::AttributeAllocator::getDefault()) {
  assign(event);
}

MessageAttributes &MessageAttributes::assign(const MessageEvent &event) {
  // Preserve the observed opaque word bits, without claiming original field
  // declarations or ARM offsets for the independent native byte storage.
  for (unsigned i = 0; i < 4; ++i) {
    opaqueAppState_[i] =
        static_cast<unsigned char>(event.header.routeA >> (i * 8));
    opaqueAppState_[i + 4] =
        static_cast<unsigned char>(event.header.routeB >> (i * 8));
  }
  removeAll();
  const auto type = event.header.type;
  if (type == 0x5a4d || type == 0x5a42) {
    Core::IO::MemoryStream stream(8192);
    // The original app ignores both status results and preserves any state
    // left by the actual source providers, including failed/partial parsing.
    (void)Core::Portable::ThreadAwareCompression::unzip(
        stream, event.data, static_cast<int>(event.sizeBits), 15);
    Core::Portable::Archiver archive(&stream,
                                     type == 0x5a42
                                         ? Core::Portable::Archiver::kUBJSON
                                         : Core::Portable::Archiver::kJSON,
                                     0);
    (void)archive.load(*this);
  } else if (type == 0x4a4d || type == 0x5542) {
    // Legacy API takes void*, but this borrowed stream is used only to read.
    // The input must remain valid across removeAll; no in-place load is used.
    Core::IO::MemoryStream stream(const_cast<void *>(event.data),
                                  event.sizeBits);
    Core::Portable::Archiver archive(&stream,
                                     type == 0x5542
                                         ? Core::Portable::Archiver::kUBJSON
                                         : Core::Portable::Archiver::kJSON,
                                     0);
    (void)archive.load(*this);
  }
  return *this;
}
} // namespace Presonus::UC
