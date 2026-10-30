#include "presonus/mixer_state/MixerState.hpp"
#include <cstring>

namespace {
std::int32_t signedWord(std::uint32_t word) {
  std::int32_t result;
  std::memcpy(&result, &word, 4);
  return result;
}
std::uint32_t unsignedWord(std::int32_t number) {
  std::uint32_t word;
  std::memcpy(&word, &number, 4);
  return word;
}
} // namespace

namespace Presonus {
bool MixerClientComponentBase::isStereoChannelType(ChannelType type) const {
  const auto word = static_cast<std::uint32_t>(type);
  return word <= 7U && ((1U << word) & 0x86U) != 0;
}
std::int32_t MixerClientComponentBase::getNumGeqs() const {
  return state_.hasGeqConfiguration ? signedWord(state_.geqCountWord) : 0;
}
std::int32_t MixerClientComponentBase::getNumMixGeqs() const {
  // Original virtual slot +0x44 invokes getNumGeqs(), including overrides.
  // Perform ARM modulo-2^32 subtraction without C++ signed overflow.
  return signedWord(unsignedWord(getNumGeqs()) - 3U);
}
std::uint32_t MixerClientComponentBase::getCascadeState() const {
  if (state_.masterWord != 0)
    return 2;
  return state_.slaveWord != 0 ? 1U : 0U;
}
bool MixerClientComponent::isAggregateMeteringChannelType(
    ChannelType type) const {
  return static_cast<std::uint32_t>(type) == 5U;
}
} // namespace Presonus
