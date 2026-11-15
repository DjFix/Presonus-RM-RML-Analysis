#include "presonus/mixer/RackMixerComponent.hpp"
#include <cstdlib>
#include <iostream>
#include <memory>
#include <new>
#include <vector>
static bool failArrays;
void *operator new[](std::size_t n) {
  if (failArrays)
    throw std::bad_alloc();
  auto *p = std::malloc(n ? n : 1);
  if (!p)
    throw std::bad_alloc();
  return p;
}
void operator delete[](void *p) noexcept { std::free(p); }
void operator delete[](void *p, std::size_t) noexcept { std::free(p); }
int main() {
  int capacity, fail, seeds, count;
  while (std::cin >> capacity >> fail >> seeds >> count) {
    Presonus::Mixer::MixerComponentBase base;
    std::uint32_t cascade = 0;
    Presonus::Mixer::RackMixerComponent rack(base, cascade);
    presonus::mute_group_port::MixerData groups;
    rack.muteGroups = &groups;
    Core::Vector<Presonus::Mixer::ChannelComponent *> channels;
    std::vector<std::unique_ptr<Presonus::Mixer::ChannelComponent>> objects;
    std::vector<presonus::mixer::ChannelState> state(count);
    std::vector<int> kinds(count);
    Core::Portable::Parameter *ids[] = {
        nullptr, reinterpret_cast<Core::Portable::Parameter *>(0x1010),
        reinterpret_cast<Core::Portable::Parameter *>(0x1020),
        reinterpret_cast<Core::Portable::Parameter *>(0x1030)};
    // Only identity is observed: borrowed mute pointers are never dereferenced.
    groups.allMutes.setDelta(1);
    groups.allMutes.resize(capacity);
    for (int i = 0, v; i < seeds; ++i) {
      std::cin >> v;
      groups.allMutes.add(ids[v]);
    }
    for (int i = 0, m; i < count; ++i) {
      std::cin >> kinds[i] >> m;
      state[i].mute = ids[m];
      objects.push_back(std::make_unique<Presonus::Mixer::ChannelComponent>(
          Presonus::Mixer::ChannelComponent::SourcePortConstruction{},
          state[i]));
      channels.add(objects.back().get());
    }
    base.sceneChannels = &channels;
    base.channelIdentity = [&](auto *p) {
      for (int i = 0; i < count; ++i)
        if (objects[i].get() == p)
          return std::pair<std::int32_t, std::int32_t>{kinds[i], i};
      std::abort();
    };
    // Native uses caller capacity exactly. CCL rounds to delta=10; set an
    // explicitly unit delta so both sides exercise the same capacity state.
    // Provider growth is intentionally tested separately from app selection.
    failArrays = fail;
    rack.setupAllMutesGroup();
    failArrays = false;
    std::cout << groups.allMutes.count();
    for (int i = 0; i < groups.allMutes.count(); ++i) {
      auto *p = groups.allMutes.at(i);
      int v = 0;
      for (int j = 1; j < 4; ++j)
        if (p == ids[j])
          v = j;
      std::cout << ' ' << v;
    }
    std::cout << '\n';
  }
}
