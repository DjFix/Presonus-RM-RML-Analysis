#include "presonus/uc/ServerRootComponent.hpp"
#include "presonus/uc/misc_events.hpp"

#include <array>
#include <cstring>
#include <iostream>

namespace {
template <typename T>
std::array<unsigned char, sizeof(T)> snapshot(const T &object) {
  std::array<unsigned char, sizeof(T)> bytes{};
  std::memcpy(bytes.data(), &object, sizeof(T));
  return bytes;
}
} // namespace

int main() {
  using namespace Presonus::UC;
  unsigned sample;
  while (std::cin >> sample) {
    if (sample > 255)
      return 1;
    const auto seed = static_cast<unsigned char>(sample);
    ServerRootComponent root("local root");
    root.setStorageTag(seed);
    MusicInputEvent event{};
    event.header.routeA = seed;
    event.idBits = seed;
    event.modeByte = seed;
    event.valueBits = 0x10000u + seed;
    const auto receiverBefore = snapshot(root);
    const auto payloadBefore = snapshot(event);
    root.receiveEvent(event);
    std::cout << sample << ' ' << (snapshot(root) == receiverBefore) << ' '
              << (snapshot(event) == payloadBefore) << '\n';
  }
}
