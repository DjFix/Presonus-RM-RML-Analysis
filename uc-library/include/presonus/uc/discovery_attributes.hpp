#pragma once

#include "core/public/corestringbuffer.h"
#include <array>
#include <cstdint>

namespace Presonus::UC {
// Portable metadata snapshot. The original names and meanings of the five
// data words and four string roles remain unresolved.
struct DiscoveryAttributes {
  DiscoveryAttributes();
  DiscoveryAttributes &operator=(const DiscoveryAttributes &);

  std::array<std::uint32_t, 5> words{};
  std::array<Core::CString64, 4> strings;
};
} // namespace Presonus::UC
