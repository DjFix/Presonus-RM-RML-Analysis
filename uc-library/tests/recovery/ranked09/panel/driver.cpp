#include "presonus/panel/GeqUIComponent.hpp"
#include "presonus/panel/PresetNameManager.hpp"
#include "presonus/panel/SPIControlGroup.hpp"
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <vector>
// Test-only required app boundary. Selector tests use explicitly bound CCL
// vectors; all unrelated app calls fail instead of supplying fabricated state.
struct Dependencies final : presonus::gequi_port::Dependencies {
  Presonus::Mixer::ChannelComponent *boundChannel = nullptr;
  int assignedCalls = 0;
  [[noreturn]] static void unused() {
    throw std::logic_error("unexpected dependency");
  }
  int geqCount() const override { return 0; }
  Presonus::Mixer::GEQComponent *geqAt(int) const override { unused(); }
  Core::Portable::Component &
  parameters(Presonus::Mixer::GEQComponent *) override {
    unused();
  }
  Core::Portable::Component &
  parameters(Presonus::Mixer::ChannelComponent *) override {
    unused();
  }
  int channelKind(Presonus::Mixer::ChannelComponent *) const override {
    return 0;
  }
  std::uint32_t
  channelIndex(Presonus::Mixer::ChannelComponent *) const override {
    unused();
  }
  Core::Portable::Parameter &
  channelLink(Presonus::Mixer::ChannelComponent *) override {
    unused();
  }
  Presonus::Mixer::ChannelComponent *assignedChannel(int) override {
    ++assignedCalls;
    return boundChannel;
  }
  bool linked(Presonus::Mixer::GEQComponent *) const override { unused(); }
  bool linkSlave(Presonus::Mixer::GEQComponent *) const override { unused(); }
  bool linked(Presonus::Mixer::ChannelComponent *) const override {
    return false;
  }
  void flatten(Presonus::Mixer::GEQComponent *) override { unused(); }
  Presonus::Mixer::GEQComponent *
  geqController(Core::Portable::IParamObserver *) override {
    unused();
  }
  Presonus::Mixer::ChannelComponent *
  channelController(Core::Portable::IParamObserver *) override {
    unused();
  }
  bool channelUpdateLink(Presonus::Mixer::ChannelComponent *) const override {
    unused();
  }
  void updateGeqNameList() override { unused(); }
};
// Explicit offline ioctl-boundary double; never touches hardware.
struct Transfer final : presonus::spi_port::Transfer {
  int calls = 0, descriptor = 0, length = 0;
  std::uint32_t request = 0;
  void submit(int fd, std::uint32_t req, const std::uint8_t *, std::uint8_t *rx,
              int len) override {
    ++calls;
    descriptor = fd;
    request = req;
    length = len;
    for (int i = 0; i < len; ++i)
      rx[i] = static_cast<std::uint8_t>(0xa0 + i);
  }
};
int main() {
  int count, index;
  std::uintptr_t error, a, b, c;
  std::string kind;
  while (std::cin >> kind) {
    if (kind == "spi") {
      int dirty, fd, width, count;
      std::cin >> dirty >> fd >> width >> count;
      std::vector<std::uint32_t> values(count);
      for (auto &v : values)
        std::cin >> v;
      Core::ConstVector<std::uint32_t> controls(values.data(), count);
      Transfer transfer;
      Presonus::Panel::SPIControlGroup group(controls, width, fd, transfer);
      group.markDirty(dirty != 0);
      group.onIdle();
      std::cout << group.isDirty();
      for (auto v : group.transmitted())
        std::cout << ' ' << unsigned(v);
      for (auto v : group.received())
        std::cout << ' ' << unsigned(v);
      std::cout << ' ' << transfer.calls << ' ' << transfer.descriptor << ' '
                << transfer.request << ' ' << transfer.length << '\n';
      continue;
    }
    if (kind == "geq") {
      int geq, mainCount, auxCount, geqCount;
      std::uintptr_t error;
      std::cin >> geq >> mainCount >> auxCount >> geqCount >> error;
      using Channel = Presonus::Mixer::ChannelComponent;
      Channel *mainItems[3], *auxItems[3];
      for (auto &v : mainItems) {
        std::uintptr_t n;
        std::cin >> n;
        v = reinterpret_cast<Channel *>(n);
      }
      for (auto &v : auxItems) {
        std::uintptr_t n;
        std::cin >> n;
        v = reinterpret_cast<Channel *>(n);
      }
      Core::ConstVector<Channel *> main(mainItems, mainCount),
          aux(auxItems, auxCount);
      Core::ConstVector<Channel *>::getError() =
          reinterpret_cast<Channel *>(error);
      presonus::gequi_port::ChannelSelection selection{main, aux, geqCount};
      std::uintptr_t nativeExpected;
      std::cin >> nativeExpected;
      Dependencies deps;
      deps.boundChannel = reinterpret_cast<Channel *>(nativeExpected);
      Presonus::Panel::GeqUIComponent component(deps);
      component.configureSelection(geq, 0);
      component.configureChannelSelection(selection);
      auto *selected = component.getChannelAssignedToCurrentGeq();
      if (selected != deps.assignedChannel(geq))
        std::abort();
      // Both old caller mode and transition to recovered selector must agree.
      deps.assignedCalls = 0;
      Presonus::Panel::GeqUIComponent legacy(deps);
      legacy.configureSelection(geq, 0);
      legacy.updateStereoField();
      if (deps.assignedCalls != 1)
        std::abort();
      int expectedCalls = 1;
      if (!selected) {
        legacy.updateStereoLink(nullptr, false);
        expectedCalls = 3;
        if (deps.assignedCalls != expectedCalls)
          std::abort();
      }
      legacy.configureChannelSelection(selection);
      legacy.updateStereoField();
      if (deps.assignedCalls != expectedCalls)
        std::abort();
      if (!selected) {
        legacy.updateStereoLink(nullptr, false);
        if (deps.assignedCalls != expectedCalls)
          std::abort();
      }
      std::cout << reinterpret_cast<std::uintptr_t>(selected) << '\n';
      continue;
    }
    std::cin >> count >> index >> error >> a >> b >> c;
    using Cache = Presonus::Panel::PresetNameCache;
    Cache *items[] = {reinterpret_cast<Cache *>(a),
                      reinterpret_cast<Cache *>(b),
                      reinterpret_cast<Cache *>(c)};
    Core::ConstVector<Cache *>::getError() = reinterpret_cast<Cache *>(error);
    Presonus::Panel::PresetNameManager manager(items, count);
    std::cout << reinterpret_cast<std::uintptr_t>(manager.getCache(index))
              << '\n';
  }
}
