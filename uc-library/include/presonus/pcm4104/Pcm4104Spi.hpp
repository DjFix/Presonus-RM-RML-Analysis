#pragma once

#include <cstdint>

namespace Presonus::PCM4104 {
// Portable source port of one observed member. Original class layout and return
// declaration are unresolved; this class does not establish binary
// compatibility.
class Pcm4104Spi {
public:
  std::uint32_t lookupChannelAttenuationRegister(int channel);
};
} // namespace Presonus::PCM4104
