#include "presonus/panel/GEQPage.hpp"
#include "presonus/panel/GeqUIComponent.hpp"
#include <iostream>
#include <stdexcept>
namespace {
int entered = 0;
}
extern "C" void __real__ZN8Presonus5Panel14GeqUIComponent17flattenCurrentGeqEv(
    Presonus::Panel::GeqUIComponent *);
extern "C" void __wrap__ZN8Presonus5Panel14GeqUIComponent17flattenCurrentGeqEv(
    Presonus::Panel::GeqUIComponent *p) {
  ++entered;
  __real__ZN8Presonus5Panel14GeqUIComponent17flattenCurrentGeqEv(p);
}
struct Dependencies final : presonus::gequi_port::Dependencies {
  int size;
  int flattened = 0;
  int geqCount() const override { return size; }
  Presonus::Mixer::GEQComponent *geqAt(int) const override { return nullptr; }
  Core::Portable::Component &
  parameters(Presonus::Mixer::GEQComponent *) override {
    throw std::logic_error("unexpected");
  }
  Core::Portable::Component &
  parameters(Presonus::Mixer::ChannelComponent *) override {
    throw std::logic_error("unexpected");
  }
  int channelKind(Presonus::Mixer::ChannelComponent *) const override {
    throw std::logic_error("unexpected");
  }
  std::uint32_t
  channelIndex(Presonus::Mixer::ChannelComponent *) const override {
    throw std::logic_error("unexpected");
  }
  Core::Portable::Parameter &
  channelLink(Presonus::Mixer::ChannelComponent *) override {
    throw std::logic_error("unexpected");
  }
  Presonus::Mixer::ChannelComponent *assignedChannel(int) override {
    throw std::logic_error("unexpected");
  }
  bool linked(Presonus::Mixer::GEQComponent *) const override {
    throw std::logic_error("unexpected");
  }
  bool linkSlave(Presonus::Mixer::GEQComponent *) const override {
    throw std::logic_error("unexpected");
  }
  bool linked(Presonus::Mixer::ChannelComponent *) const override {
    throw std::logic_error("unexpected");
  }
  void flatten(Presonus::Mixer::GEQComponent *) override { ++flattened; }
  Presonus::Mixer::GEQComponent *
  geqController(Core::Portable::IParamObserver *) override {
    return nullptr;
  }
  Presonus::Mixer::ChannelComponent *
  channelController(Core::Portable::IParamObserver *) override {
    return nullptr;
  }
  bool channelUpdateLink(Presonus::Mixer::ChannelComponent *) const override {
    throw std::logic_error("unexpected");
  }
  void updateGeqNameList() override { throw std::logic_error("unexpected"); }
};
int main() {
  int present, selection, count;
  while (std::cin >> present >> selection >> count) {
    Dependencies d;
    d.size = count;
    Presonus::Panel::GeqUIComponent component(d);
    component.configureSelection(selection, 0);
    Presonus::Panel::GEQPage page(present ? &component : nullptr);
    entered = 0;
    page.recall();
    if (page.portableComponent() != (present ? &component : nullptr))
      return 1;
    std::cout << d.flattened << ' ' << component.selectedBand() << ' '
              << entered << '\n';
  }
}
