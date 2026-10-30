#pragma once
#include "presonus/uc/events.hpp"
namespace Presonus::UC {
// Portable storage with observed ARM data fields at +16,+20,+24,+26,+28,
// and four 64-byte byte strings at +36,+100,+164,+228. Original names,
// inheritance, constructors and ABI are unproved. Sign bit of version enables
// extension fields. Strings contain arbitrary bytes, not assumed UTF-8.
struct DiscoveryAliveEvent {
  Event header;
  std::uint32_t versionBits = 0, extensionBits = 0;
  unsigned short extensionA = 0, extensionB = 0;
  std::array<unsigned char, 8> extensionBytes{};
  std::array<std::array<char, 64>, 4> strings{};
};
class DiscoveryAliveEventClass {
public:
  // Original non-template return spelling is unencoded; bool matches 0/1.
  bool write(BufferWriter &, const DiscoveryAliveEvent &) const;
  bool read(DiscoveryAliveEvent &, BufferReader &) const;
};
} // namespace Presonus::UC
