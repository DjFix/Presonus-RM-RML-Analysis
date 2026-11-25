#include "presonus/uc/ClientRootComponent.hpp"
#include "presonus/uc/client_event_values.hpp"

#include <array>
#include <cstring>
#include <iostream>
#include <string_view>

template <typename T> auto snapshot(const T &object) {
  std::array<unsigned char, sizeof(T)> bytes{};
  std::memcpy(bytes.data(), &object, bytes.size());
  return bytes;
}

int main() {
  using namespace Presonus::UC;
  for (const char *name : {"", "root"}) {
    ClientRootComponent root(name);

    MeterEvent8 payload{};
    payload.source = 9;
    MeterEvent input{payload.header,
                     payload.keyBits,
                     payload.source,
                     payload.count,
                     payload.recordCount,
                     payload.reserved25,
                     payload.records,
                     payload.data.data(),
                     payload.data.size(),
                     1,
                     &payload};

    const auto rootBytes = snapshot(root);
    const auto inputBytes = snapshot(input);
    root.updateLevels(input);
    if (rootBytes != snapshot(root) || inputBytes != snapshot(input) ||
        root.getRoot() != &root || std::string_view(root.getName()) != name)
      return 1;
    std::cout << "unchanged\n";
  }
}
