#include "presonus/pcm4104/Pcm4104Spi.hpp"

namespace Presonus::PCM4104 {
std::uint32_t Pcm4104Spi::lookupChannelAttenuationRegister(int channel) {
  // ARM ADD wraps in 32 bits, including channel == INT_MAX.
  return static_cast<std::uint32_t>(channel) + std::uint32_t{1};
}
} // namespace Presonus::PCM4104
