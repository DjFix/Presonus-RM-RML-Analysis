#include "presonus/mixer/AutoFilterGroupManager.hpp"
#include <array>
#include <cstdlib>
#include <iostream>
#include <new>
static bool failArrays;
void *operator new[](std::size_t n) {
  if (failArrays)
    throw std::bad_alloc();
  if (auto *p = std::malloc(n ? n : 1))
    return p;
  throw std::bad_alloc();
}
void operator delete[](void *p) noexcept { std::free(p); }
void operator delete[](void *p, std::size_t) noexcept { std::free(p); }
int main() {
  int capacity, fail, count, pointer;
  while (std::cin >> capacity >> fail >> count >> pointer) {
    std::array<int, 2> tokens{};
    Presonus::Mixer::ChannelComponent *ids[] = {
        nullptr,
        reinterpret_cast<Presonus::Mixer::ChannelComponent *>(&tokens[0]),
        reinterpret_cast<Presonus::Mixer::ChannelComponent *>(&tokens[1])};
    // Identity-only pointers are intentionally never dereferenced.
    Presonus::Mixer::AutoFilterGroupManager manager(
        Presonus::Mixer::AutoFilterGroupManager::SourcePortConstruction{},
        capacity, 1);
    for (int i = 0, v; i < count; ++i) {
      std::cin >> v;
      manager.addUpdateChannel(ids[v]);
    }
    const auto &items = manager.portableUpdateChannels();
    failArrays = fail;
    manager.addUpdateChannel(ids[pointer]);
    failArrays = false;
    std::cout << items.count();
    for (int i = 0; i < items.count(); ++i) {
      int v = 0;
      for (int j = 1; j < 3; ++j)
        if (items.at(i) == ids[j])
          v = j;
      std::cout << ' ' << v;
    }
    std::cout << '\n';
  }
}
