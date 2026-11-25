#include "presonus/panel/SharedMemoryComm.hpp"

#include <array>
#include <cstring>
#include <iostream>
#include <memory>
#include <new>

int main() {
  using Presonus::Panel::SharedMemoryComm;

  for (unsigned fill : {0x35, 0xC2}) {
    alignas(SharedMemoryComm) unsigned char storage[sizeof(SharedMemoryComm)];
    std::memset(storage, fill, sizeof(storage));
    auto *receiver = new (storage) SharedMemoryComm;

    std::array<unsigned char, sizeof(SharedMemoryComm)> before{};
    std::memcpy(before.data(), receiver, before.size());
    receiver->close();
    const bool unchanged =
        std::memcmp(before.data(), receiver, before.size()) == 0;
    std::destroy_at(receiver);
    std::cout << fill << " " << unchanged << "\n";
  }
}
