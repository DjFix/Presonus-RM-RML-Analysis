#include "presonus/mixer/StormMixerComponent.hpp"
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <new>
#include <string>

using namespace Core::Portable;
using namespace Presonus::Mixer;
using namespace presonus::mixer_component_port;
namespace {
void *watched = nullptr;
void *baseVptr = nullptr;
int frees = 0, atFreeBase = 0, childDeaths = 0;
void *vptr(void *p) {
  void *v;
  std::memcpy(&v, p, sizeof(v));
  return v;
}
struct Child : Component {
  ~Child() override { ++childDeaths; }
};
const ParamInfo parameters[] = {
    PARAM_FLOAT(17, "level", 0, 1, 0.25f, 0.01f, "", 0, 0, 0),
    PARAM_STRING(18, "name", 0)};
// App-service fixture. All production base operations are forbidden during
// destruction; the real defaulted destructor has only borrowed references.
struct Services : MixerServices {
  Component resources{"resources"};
  void serverParamChanged(MixerComponent &, Parameter *, int) override {
    std::abort();
  }
  Component &parameterComponent(ChannelComponent &) const override {
    return const_cast<Component &>(resources);
  }
  Presonus::LinkableComponent *linkIdentity(ChannelComponent *) const override {
    std::abort();
  }
  const IStorageFilter *storageFilter(int, bool) override { std::abort(); }
  void load(const InputStorage &) override { std::abort(); }
  void save(OutputStorage &) override { std::abort(); }
  bool muteExcluded(const ChannelComponent &) const override { std::abort(); }
  Parameter &muteSource(ChannelComponent &) override { std::abort(); }
  Parameter &muteDestination(ChannelComponent &) override { std::abort(); }
  Parameter &selection(ChannelComponent &) override { std::abort(); }
  const char *
  presetType(const Presonus::Panel::PresetComponent &) const override {
    std::abort();
  }
  void command(const char *, const char *, int) override { std::abort(); }
};
struct LinkBoundary : Presonus::linkable_port::Boundary {
  Presonus::LinkableComponent *query(Presonus::LinkableComponent &,
                                     std::uint32_t) override {
    std::abort();
  }
  void remove(Presonus::LinkableComponent &) override { std::abort(); }
  void set(Presonus::LinkableComponent &, Presonus::LinkableComponent &,
           bool) override {
    std::abort();
  }
  void master(Presonus::LinkableComponent &,
              Presonus::LinkableComponent &) override {
    std::abort();
  }
};
} // namespace
extern "C" void realDelete(void *) asm("__real__ZdlPv");
extern "C" void wrappedDelete(void *p) asm("__wrap__ZdlPv");
extern "C" void wrappedDelete(void *p) {
  if (p && p == watched) {
    ++frees;
    atFreeBase += vptr(p) == baseVptr;
    watched = nullptr;
  }
  realDelete(p);
}
extern "C" void stormD2(StormMixerComponent *) asm(
    "_ZN8Presonus5Mixer19StormMixerComponentD2Ev");

int main(int argc, char **argv) {
  if (argc != 4)
    return 1;
  bool boundary = std::string(argv[1]) == "--boundary";
  bool deleting = std::string(argv[2]) == "d0";
  int count = std::stoi(argv[3]);
  int preserved = 0, baseSeen = 0, targetFrees = 0, targetAtFree = 0;
  {
    Services services;
    auto *channel =
        new ChannelComponent(ChannelComponent::SourcePortConstruction{});
    auto *child = new Child;
    child->addParameters(parameters, 2);
    child->getParameterByTag(17)->setValue(0.75f, false);
    static_cast<StringParam *>(child->getParameterByTag(18))
        ->fromString("borrowed-live", false);
    channel->addChild(child);
    services.resources.addChild(channel);
    Presonus::linkable_port::State linkState;
    LinkBoundary linkBoundary;
    Presonus::LinkableComponent link(linkState, linkBoundary);
    MixerState state;
    for (int i = 0; i < count; ++i) {
      state.equalizers.add(&link);
      state.channels.add(channel);
    }
    state.muteEnabled = true;
    state.cascadeDirty = true;
    // Independently constructed actual base provides the source-port vptr
    // reference and real native-boundary cleanup, never fake Core classes.
    MixerComponent baseReference(state, services);
    baseVptr = vptr(&baseReference);
    void *raw = ::operator new(boundary ? sizeof(MixerComponent)
                                        : sizeof(StormMixerComponent));
    MixerComponent *base =
        boundary ? new (raw) MixerComponent(state, services)
                 : static_cast<MixerComponent *>(new (raw) StormMixerComponent(
                       StormMixerComponent::SourcePortConstruction{}, state,
                       services));
    watched = raw;
    if (boundary) {
      std::cout << "READY\n" << std::flush;
      std::string command;
      bool destroyed = false, freed = false;
      while (std::cin >> command) {
        if (command == "B" && !destroyed) {
          base->MixerComponent::~MixerComponent();
          destroyed = true;
          baseSeen = vptr(raw) == baseVptr;
          std::cout << "BASE " << baseSeen << '\n' << std::flush;
        } else if (command == "F" && destroyed && !freed && deleting) {
          ::operator delete(raw);
          freed = true;
          std::cout << "FREE " << frees << '\n' << std::flush;
        } else if (command == "E" && destroyed && freed == deleting)
          break;
        else
          return 2;
      }
    } else if (deleting) {
      delete base;
      baseSeen = atFreeBase == 1;
    } else {
      stormD2(static_cast<StormMixerComponent *>(base));
      baseSeen = vptr(raw) == baseVptr;
    }
    targetFrees = frees;
    targetAtFree = atFreeBase;
    preserved =
        childDeaths == 0 && state.equalizers.count() == count &&
        state.muteEnabled && state.cascadeDirty &&
        services.resources.getChild(0) == channel &&
        channel->getChild(0) == child && state.channels.count() == count &&
        child->getParameterByTag(17)->getValue() == 0.75f &&
        std::strcmp(static_cast<StringParam *>(child->getParameterByTag(18))
                        ->getText()
                        .str(),
                    "borrowed-live") == 0;
    for (int i = 0; i < count; ++i)
      preserved &=
          state.equalizers.at(i) == &link && state.channels.at(i) == channel;
    if (!deleting) {
      watched = nullptr;
      ::operator delete(raw);
    }
  }
  // The actual CCL Component destructor owns and destroys its child only when
  // the external resource owner ends; derived destruction must not do so.
  std::cout << "RESULT " << baseSeen << ' ' << targetFrees << ' '
            << targetAtFree << ' ' << preserved << ' ' << childDeaths << '\n';
  return !(baseSeen && targetFrees == int(deleting) &&
           targetAtFree == int(deleting) && preserved && childDeaths == 1);
}
