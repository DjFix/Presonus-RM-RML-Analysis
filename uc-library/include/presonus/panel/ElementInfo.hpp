#pragma once
#include <array>
#include <cstdint>
#include <cstring>
namespace Presonus::Panel {
// Independent source-port input record. Offsets describe observed input bytes,
// never the host Element object or an ARM binary-compatible declaration.
struct ElementInfo {
  std::array<unsigned char, 96> observation{};
  int word(unsigned offset) const {
    const auto *p = observation.data() + offset;
    return static_cast<std::int32_t>(
        std::uint32_t(p[0]) | (std::uint32_t(p[1]) << 8) |
        (std::uint32_t(p[2]) << 16) | (std::uint32_t(p[3]) << 24));
  }
  const char *name() const {
    return reinterpret_cast<const char *>(observation.data() + 20);
  }
};
} // namespace Presonus::Panel
