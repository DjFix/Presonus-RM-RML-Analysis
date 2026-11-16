#include "presonus/mixer/GEQComponent.hpp"
#include "presonus/mixer/MixerComponent.hpp"
#include <array>
#include <iostream>
#include <memory>
#include <stdexcept>
struct UnusedMixerServices final
    : presonus::mixer_component_port::MixerServices {
  [[noreturn]] static void fail() {
    throw std::logic_error("unexpected Mixer service call");
  }
  void serverParamChanged(Presonus::Mixer::MixerComponent &,
                          Core::Portable::Parameter *, int) override {
    fail();
  }
  Core::Portable::Component &
  parameterComponent(Presonus::Mixer::ChannelComponent &) const override {
    fail();
  }
  Presonus::LinkableComponent *
  linkIdentity(Presonus::Mixer::ChannelComponent *) const override {
    fail();
  }
  const Core::Portable::IStorageFilter *storageFilter(int, bool) override {
    fail();
  }
  void load(const Core::Portable::InputStorage &) override { fail(); }
  void save(Core::Portable::OutputStorage &) override { fail(); }
  bool muteExcluded(const Presonus::Mixer::ChannelComponent &) const override {
    fail();
  }
  Core::Portable::Parameter &
  muteSource(Presonus::Mixer::ChannelComponent &) override {
    fail();
  }
  Core::Portable::Parameter &
  muteDestination(Presonus::Mixer::ChannelComponent &) override {
    fail();
  }
  Core::Portable::Parameter &
  selection(Presonus::Mixer::ChannelComponent &) override {
    fail();
  }
  const char *
  presetType(const Presonus::Panel::PresetComponent &) const override {
    fail();
  }
  void command(const char *, const char *, int) override { fail(); }
};
struct LinkBoundary final : Presonus::linkable_port::Boundary {
  std::array<Presonus::LinkableComponent *, 5> identities{};
  int setCount{}, removeCount{}, masterCount{}, receiver{}, partner{}, flag{};
  int id(Presonus::LinkableComponent &v) {
    for (int i = 0; i < 5; ++i)
      if (identities[i] == &v)
        return i + 1;
    throw std::logic_error("unknown identity");
  }
  Presonus::LinkableComponent *query(Presonus::LinkableComponent &,
                                     std::uint32_t) override {
    throw std::logic_error("unexpected query");
  }
  void remove(Presonus::LinkableComponent &v) override {
    ++removeCount;
    receiver = id(v);
  }
  void set(Presonus::LinkableComponent &v, Presonus::LinkableComponent &p,
           bool f) override {
    ++setCount;
    receiver = id(v);
    partner = id(p);
    flag = f;
  }
  void master(Presonus::LinkableComponent &,
              Presonus::LinkableComponent &) override {
    ++masterCount;
  }
};
static LinkBoundary *activeBoundary;
static int entrySlot, entryReceiver, entryPartner, entryFlag;
extern "C" void __real__ZN8Presonus17LinkableComponent7setLinkERS0_b(
    Presonus::LinkableComponent *, Presonus::LinkableComponent &, bool);
extern "C" void __wrap__ZN8Presonus17LinkableComponent7setLinkERS0_b(
    Presonus::LinkableComponent *receiver, Presonus::LinkableComponent &partner,
    bool flag) {
  entrySlot = 60;
  entryReceiver = activeBoundary->id(*receiver);
  entryPartner = activeBoundary->id(partner);
  entryFlag = flag;
  __real__ZN8Presonus17LinkableComponent7setLinkERS0_b(receiver, partner, flag);
}
extern "C" void __real__ZN8Presonus17LinkableComponent10removeLinkEv(
    Presonus::LinkableComponent *);
extern "C" void __wrap__ZN8Presonus17LinkableComponent10removeLinkEv(
    Presonus::LinkableComponent *receiver) {
  entrySlot = 64;
  entryReceiver = activeBoundary->id(*receiver);
  __real__ZN8Presonus17LinkableComponent10removeLinkEv(receiver);
}
int main() {
  int count, target, link, seeded;
  while (std::cin >> count >> target >> link >> seeded) {
    LinkBoundary boundary;
    activeBoundary = &boundary;
    entrySlot = entryReceiver = entryPartner = entryFlag = 0;
    std::array<Presonus::linkable_port::State, 5> states;
    std::array<std::unique_ptr<Presonus::LinkableComponent>, 5> links;
    std::array<std::unique_ptr<Presonus::Mixer::GEQComponent>, 5> geqs;
    for (int i = 0; i < 5; ++i) {
      links[i] =
          std::make_unique<Presonus::LinkableComponent>(states[i], boundary);
      boundary.identities[i] = links[i].get();
      geqs[i] = std::make_unique<Presonus::Mixer::GEQComponent>(
          Presonus::Mixer::GEQComponent::SourcePortConstruction{});
    }
    if (seeded) {
      states[target - 1].partner = links[target % 5].get();
      states[target - 1].enabled = 1;
    }
    presonus::mixer_component_port::MixerState state;
    for (int i = 0; i < 5; ++i)
      state.geqLinkIdentities.add({geqs[i].get(), links[i].get()});
    for (int i = 0; i < count; ++i) {
      int entry;
      std::cin >> entry;
      state.equalizers.add(entry ? links[entry - 1].get() : nullptr);
    }
    UnusedMixerServices services;
    Presonus::Mixer::MixerComponent mixer(state, services);
    mixer.doLink(geqs[target - 1].get(), link);
    std::cout << entrySlot << ' ' << entryReceiver << ' ' << entryPartner << ' '
              << entryFlag << ' ' << boundary.setCount << ' '
              << boundary.removeCount << ' ' << boundary.masterCount << '\n';
  }
}
