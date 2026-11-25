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
    TimeCodeEvent event{};
    event.header.routeA = seed;
    event.keyBits = seed;
    event.recordCount = 1;
    event.records[0].rawBytes[7] = seed;
    const auto receiverBefore = snapshot(root);
    const auto payloadBefore = snapshot(event);
    root.receiveEvent(event);
    std::cout << sample << ' ' << (snapshot(root) == receiverBefore) << ' '
              << (snapshot(event) == payloadBefore) << '\n';
  }
}
