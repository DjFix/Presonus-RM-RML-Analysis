#pragma once

#include "core/public/corestringbuffer.h"
#include <cstdint>

namespace Presonus::UC {

// Portable metadata value. The application readers establish these logical
// roles. Field declarations, host layout and serialization are independent of
// the original ARM representation.
struct ServerDescription {
  ServerDescription();

  int identifier = 0;
  std::uint32_t contextKind = 0;
  Core::CString64 hostAddress;
  Core::CString64 hostName;
  std::uint16_t port = 0;
  Core::CString64 applicationName;
  Core::CString64 applicationVersion;
  Core::CString64 category;
  Core::CString64 cid;
  Core::CString64 pid;
  std::uint32_t flags = 0;
};
} // namespace Presonus::UC
