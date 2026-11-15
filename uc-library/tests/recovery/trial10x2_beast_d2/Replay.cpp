#include "presonus/mixer/BeastMixerComponent.hpp"
#include <cassert>
#include <cstdlib>
#include <iostream>
#include <new>
#include <string>
using namespace Presonus::Mixer;
using namespace Core::Portable;
static void *watched;
static int frees;
extern "C" void __real__ZdlPv(void *);
extern "C" void __wrap__ZdlPv(void *p) {
  if (p == watched) {
    ++frees;
    watched = nullptr;
  }
  __real__ZdlPv(p);
}
struct Services final : presonus::mixer_component_port::MixerServices {
  [[noreturn]] static void unused() { std::abort(); }
  void serverParamChanged(MixerComponent &, Parameter *, int) override {
    unused();
  }
  Component &parameterComponent(ChannelComponent &) const override { unused(); }
  Presonus::LinkableComponent *linkIdentity(ChannelComponent *) const override {
    unused();
  }
  const IStorageFilter *storageFilter(int, bool) override { unused(); }
  void load(const InputStorage &) override { unused(); }
  void save(OutputStorage &) override { unused(); }
  bool muteExcluded(const ChannelComponent &) const override { unused(); }
  Parameter &muteSource(ChannelComponent &) override { unused(); }
  Parameter &muteDestination(ChannelComponent &) override { unused(); }
  Parameter &selection(ChannelComponent &) override { unused(); }
  const char *
  presetType(const Presonus::Panel::PresetComponent &) const override {
    unused();
  }
  void command(const char *, const char *, int) override { unused(); }
};
struct Observer final : IParamObserver {
  void *castTo(TypeID id) override {
    return id == IParamObserver::kTypeID ? this : nullptr;
  }
  int destroyed = 0;
  void paramChanged(Parameter *, int msg) override {
    if (msg == Parameter::kDestroyed)
      ++destroyed;
  }
};
extern "C" void beastD2(BeastMixerComponent *) asm(
    "_ZN8Presonus5Mixer19BeastMixerComponentD2Ev");
extern "C" void beastD0(BeastMixerComponent *) asm(
    "_ZN8Presonus5Mixer19BeastMixerComponentD0Ev");
int main(int argc, char **argv) {
  int count;
  std::cin >> count;
  assert(count > 0 && count <= 32);
  Observer observer;
  Services services;
  presonus::mixer_component_port::MixerState state;
  ParamInfo info{};
  info.type = ParamInfo::kInt;
  info.tag = 77;
  info.minValue = 0;
  info.maxValue = 100;
  ChannelComponent *channel =
      new ChannelComponent(ChannelComponent::SourcePortConstruction{});
  channel->addParameters(&info, 1);
  auto *param = channel->getParameterByTag(77);
  assert(param);
  param->setValue(37, false);
  param->addObserver(&observer);
  for (int i = 0; i < count; ++i)
    state.channels.add(channel);
  state.muteEnabled = true;
  auto *object = new BeastMixerComponent(
      BeastMixerComponent::SourcePortConstruction{}, state, services);
  watched = object;
  const bool boundary = argc > 1 && std::string(argv[1]) == "boundary";
  bool destroyed = false, freed = false;
  std::string command;
  while (std::cin >> command) {
    if (command == "BASE") {
      assert(boundary && !destroyed);
      object->MixerComponent::~MixerComponent();
      destroyed = true;
      std::cout << "1\n" << std::flush;
    } else if (command == "FREE") {
      assert(boundary && destroyed && !freed);
      ::operator delete(static_cast<void *>(object));
      freed = true;
      assert(frees == 1);
      std::cout << "1\n" << std::flush;
    } else if (command == "D2" || command == "D0") {
      assert(!boundary && !destroyed);
      if (command == "D0") {
        beastD0(object);
        freed = true;
      } else
        beastD2(object);
      destroyed = true;
      std::cout << "1\n" << std::flush;
    } else if (command == "REPORT") {
      assert(destroyed);
      bool preserved = state.channels.count() == count && state.muteEnabled &&
                       param->getValue() == 37 && observer.destroyed == 0;
      for (int i = 0; i < count; ++i)
        preserved &= state.channels.at(i) == channel;
      std::cout << frees << " " << preserved << " " << observer.destroyed
                << "\n"
                << std::flush;
    } else if (command == "CLEAN") {
      assert(destroyed);
      // Harness-owned storage and borrowed resources are released only after
      // the lifecycle observation. D2 itself must never free object storage.
      watched = nullptr;
      if (!freed)
        ::operator delete(static_cast<void *>(object));
      state.channels.removeAll();
      delete channel; // Actual Channel/Core provider cleanup emits kDestroyed.
      std::cout << observer.destroyed << "\n" << std::flush;
      return observer.destroyed == 1 ? 0 : 1;
    } else
      return 2;
  }
  return 3;
}
