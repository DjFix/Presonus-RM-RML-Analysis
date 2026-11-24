#include "presonus/mixer_state/MixerState.hpp"
#include <array>
#include <cstddef>
#include <cstdio>
#include <cstring>
#include <memory>

int main() {
  using Presonus::IPresetHandler;
  alignas(IPresetHandler) std::array<std::byte, sizeof(IPresetHandler)> storage;
  storage.fill(std::byte{0xa5});
  auto *handler =
      std::construct_at(reinterpret_cast<IPresetHandler *>(storage.data()));
  std::array<unsigned char, sizeof(IPresetHandler)> before{};
  std::memcpy(before.data(), handler, before.size());
  const auto &receiver = *handler;
  const char *first = receiver.getEmptyPresetString();
  const bool stable = first && receiver.getEmptyPresetString() == first;
  const bool intact = std::memcmp(before.data(), handler, before.size()) == 0;
  std::destroy_at(handler);
  const IPresetHandler other;
  if (!stable || !intact || other.getEmptyPresetString() != first)
    return 1;
  std::printf("%02x\n", static_cast<unsigned char>(*first));
}
