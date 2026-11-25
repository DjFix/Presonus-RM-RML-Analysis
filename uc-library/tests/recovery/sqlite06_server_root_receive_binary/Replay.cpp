#include "presonus/uc/ServerRootComponent.hpp"
#include "presonus/uc/data_codecs.hpp"

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
    std::array<unsigned char, 4> data{seed, 1, 128, 255};
    const auto dataBefore = data;
    BinaryEvent event{};
    event.header.routeA = seed;
    event.data = data.data();
    event.sizeBits = data.size() * 8;
    event.word24 = seed;
    const auto receiverBefore = snapshot(root);
    const auto payloadBefore = snapshot(event);
    root.receiveEvent(event);
    std::cout << sample << ' ' << (snapshot(root) == receiverBefore) << ' '
              << (snapshot(event) == payloadBefore && data == dataBefore)
              << '\n';
  }
}
