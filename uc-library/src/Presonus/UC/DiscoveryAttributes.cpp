#include "presonus/uc/discovery_attributes.hpp"
#include <cstring>

namespace Presonus::UC {
DiscoveryAttributes::DiscoveryAttributes() {
  for (auto &value : strings)
    std::memset(value.getBuffer(), 0, value.getSize());
}

DiscoveryAttributes &
DiscoveryAttributes::operator=(const DiscoveryAttributes &) = default;
} // namespace Presonus::UC
