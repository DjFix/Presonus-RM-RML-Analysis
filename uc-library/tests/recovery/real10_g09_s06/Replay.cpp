#include "core/system/coredebug.h"
#include "presonus/mixer/MixerComponent.hpp"
#include "presonus/mixer/PermissionsComponent.hpp"
#include <array>
#include <cstring>
#include <iostream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <unordered_map>
#include <vector>
static std::ostringstream trace;
static bool recording;
static presonus::mixer_component_port::MixerState *active;
static std::unordered_map<const void *, int> channelIds, linkIds, paramIds;
static std::vector<Presonus::LinkableComponent *> links;
static int masters, loads, permissionsChanged;
static std::array<Core::Portable::Parameter *, 4> selectionParams;
static int guard() { return active->selectionGuard; }
extern "C" Core::Portable::Parameter *
__real__ZNK4Core8Portable9Component17getParameterByTagEi(
    const Core::Portable::Component *, int);
extern "C" Core::Portable::Parameter *
__wrap__ZNK4Core8Portable9Component17getParameterByTagEi(
    const Core::Portable::Component *p, int tag) {
  if (recording)
    trace << "G:" << channelIds.at(p) << ':' << tag << ':' << guard() << ';';
  return __real__ZNK4Core8Portable9Component17getParameterByTagEi(p, tag);
}
extern "C" void __real__ZN8Presonus17LinkableComponent7setLinkERS0_b(
    Presonus::LinkableComponent *, Presonus::LinkableComponent &, bool);
extern "C" void __wrap__ZN8Presonus17LinkableComponent7setLinkERS0_b(
    Presonus::LinkableComponent *p, Presonus::LinkableComponent &other,
    bool inverse) {
  if (recording)
    trace << "L:" << linkIds.at(p) << ':' << linkIds.at(&other) << ':'
          << inverse << ':' << guard() << ';';
  __real__ZN8Presonus17LinkableComponent7setLinkERS0_b(p, other, inverse);
}
extern "C" void __real__ZN8Presonus5Mixer16ChannelComponent10removeLinkEv(
    Presonus::Mixer::ChannelComponent *);
extern "C" void __wrap__ZN8Presonus5Mixer16ChannelComponent10removeLinkEv(
    Presonus::Mixer::ChannelComponent *p) {
  if (recording)
    trace << "U:" << channelIds.at(p) << ':' << guard() << ';';
  __real__ZN8Presonus5Mixer16ChannelComponent10removeLinkEv(p);
}
extern "C" void
__real__ZN8Presonus5Mixer20PermissionsComponent17auxLinkingChangedEv(
    Presonus::Mixer::PermissionsComponent *);
extern "C" void
__wrap__ZN8Presonus5Mixer20PermissionsComponent17auxLinkingChangedEv(
    Presonus::Mixer::PermissionsComponent *p) {
  if (recording)
    trace << "P:" << guard() << ';';
  __real__ZN8Presonus5Mixer20PermissionsComponent17auxLinkingChangedEv(p);
}
struct Watch final : Core::Portable::IParamObserver {
  void *castTo(TypeID t) override {
    return t == IParamObserver::kTypeID ? static_cast<IParamObserver *>(this)
                                        : nullptr;
  }
  void paramChanged(Core::Portable::Parameter *p, int message) override {
    if (message != Core::Portable::Parameter::kChanged)
      throw std::logic_error("unexpected edited parameter");
    float f = p->getValue();
    unsigned bits;
    std::memcpy(&bits, &f, 4);
    if (recording)
      trace << "S:" << paramIds.at(p) << ':' << bits << ":0:" << guard() << ';';
  }
};
struct Boundary final : Presonus::linkable_port::Boundary {
  [[noreturn]] static void fail() {
    throw std::logic_error("unexpected link boundary");
  }
  Presonus::LinkableComponent *query(Presonus::LinkableComponent &,
                                     std::uint32_t) override {
    fail();
  }
  void remove(Presonus::LinkableComponent &) override { fail(); }
  void set(Presonus::LinkableComponent &, Presonus::LinkableComponent &,
           bool) override {
    fail();
  }
  void master(Presonus::LinkableComponent &,
              Presonus::LinkableComponent &) override {
    ++masters;
  }
};
struct ChannelServices final : presonus::mixer::ChannelApplicationServices {
  bool isLinked(const Presonus::Mixer::ChannelComponent &c) const override {
    return links.at(channelIds.at(&c) - 1)->isLinked();
  }
  void removeLink(Presonus::Mixer::ChannelComponent &c) override {
    links.at(channelIds.at(&c) - 1)->removeLink();
  }
  Presonus::Mixer::ChannelComponent *
  linkablePair(Presonus::Mixer::ChannelComponent &) override {
    throw std::logic_error("unexpected pair");
  }
  void faderLocateDirty(Presonus::Mixer::ChannelComponent &) override {
    throw std::logic_error("unexpected locate");
  }
  void coefficientsChanged(Presonus::Mixer::ChannelComponent &, bool) override {
    throw std::logic_error("unexpected coefficients");
  }
};
struct Delegate final : Presonus::Mixer::MixerComponentBase::Delegate {
  int id;
  explicit Delegate(int i) : id(i) {}
  void selectionChanged() override {
    if (recording)
      trace << "O:" << id << ':' << guard() << ';';
  }
  void linkChanged() override {
    if (recording)
      trace << "D:" << id << ':' << guard() << ';';
  }
  void clientsChanged() override {
    throw std::logic_error("unexpected clients");
  }
  void notifyStoring(bool) override {
    throw std::logic_error("unexpected store");
  }
  void faderLocateDirty(Presonus::Mixer::ChannelComponent *) override {
    throw std::logic_error("unexpected fader");
  }
};
static void loaded(void *, Presonus::Mixer::PermissionsComponent &) { ++loads; }
static void changed(void *, Presonus::Mixer::PermissionsComponent &) {
  ++permissionsChanged;
}
struct Services final : presonus::mixer_component_port::MixerServices {
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
  linkIdentity(Presonus::Mixer::ChannelComponent *c) const override {
    return links.at(channelIds.at(c) - 1);
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
  selection(Presonus::Mixer::ChannelComponent &c) override {
    return *selectionParams.at(channelIds.at(&c) - 1);
  }
  const char *
  presetType(const Presonus::Panel::PresetComponent &) const override {
    fail();
  }
  void command(const char *, const char *, int) override { fail(); }
};

int main(int argc, char **argv) {
  bool selection =
      argc == 2 && (std::string(argv[1]) == "--selection" ||
                    std::string(argv[1]) == "--selection-provider");
  bool selectionProvider =
      argc == 2 && std::string(argv[1]) == "--selection-provider";
  bool provider = argc == 2 && std::string(argv[1]) == "--provider";
  int kind, link, hasPartner, delegates, withPermissions, initialGuard;
  while (std::cin >> kind >> link >> hasPartner >> delegates >>
         withPermissions >> initialGuard) {
    recording = false;
    trace.str("");
    trace.clear();
    channelIds.clear();
    linkIds.clear();
    paramIds.clear();
    links.clear();
    masters = loads = permissionsChanged = 0;
    presonus::mixer_component_port::MixerState state;
    active = &state;
    state.selectionGuard = initialGuard;
    Boundary boundary;
    ChannelServices channelServices;
    Services services;
    std::array<Presonus::linkable_port::State, 4> linkStates;
    std::array<presonus::mixer::ChannelState, 4> channelStates;
    std::array<Core::Portable::ParamInfo, 4> infos;
    std::array<Watch, 4> watches;
    std::vector<std::unique_ptr<Presonus::LinkableComponent>> linkObjects;
    std::vector<std::unique_ptr<Presonus::Mixer::ChannelComponent>> channels;
    std::array<Core::Portable::Parameter *, 4> params{};
    for (int i = 0; i < 4; ++i) {
      linkObjects.push_back(std::make_unique<Presonus::LinkableComponent>(
          linkStates[i], boundary));
      links.push_back(linkObjects.back().get());
      linkIds[links.back()] = i + 1;
      channels.push_back(std::make_unique<Presonus::Mixer::ChannelComponent>(
          channelStates[i], channelServices));
      channelIds[channels.back().get()] = i + 1;
      infos[i] = PARAM_FLOAT(21, "linked", 0.f, 1.f, .25f, .01f, nullptr,
                             nullptr, 0.f, 0);
      channels.back()->addParameters(&infos[i], 1);
      params[i] = channels.back()->getParameterByTag(21);
      paramIds[params[i]] = i + 1;
      params[i]->addObserver(&watches[i]);
      state.channelLinks.add(
          {channels.back().get(), links.back(), &linkStates[i], i ? 0 : kind});
    }
    std::array<Core::Vector<Presonus::Mixer::ChannelComponent *>, 3> views;
    for (int i = 0; i < 3; ++i) {
      views[i].add(channels[0].get());
      if (hasPartner)
        views[i].add(channels[i + 1].get());
    }
    state.linkKind0To3 = &views[0];
    state.linkKind4 = &views[1];
    state.linkKind6 = &views[2];
    Presonus::Mixer::MixerComponentBase base;
    Delegate first(0), second(1);
    if (delegates) {
      base.delegates.add(&first);
      base.delegates.add(&second);
    }
    state.delegates = &base.delegates;
    Presonus::Mixer::PermissionsBindings bindings;
    bindings.loadSelectedDevice = loaded;
    bindings.devicePermissionsChanged = changed;
    Presonus::Mixer::PermissionsComponent permission(bindings);
    if (withPermissions)
      state.linkPermissions = &permission;
    Presonus::Mixer::MixerComponent mixer(state, services);
    selectionParams = params;
    recording = true;
    if (selection) {
      state.selectedChannel = channels[2].get();
      if (selectionProvider) {
        // Exact unchanged native04 schedule: debug, set, changed, two
        // delegates.
        params[0]->setValue(1.f, false);
        params[0]->changed();
        first.selectionChanged();
        second.selectionChanged();
      } else
        mixer.doSelect(channels[0].get());
      recording = false;
      std::cout << "SELECT_RESULT " << trace.str() << '|'
                << state.cascadeSelected << ' ' << state.cascadeDirty << '|'
                << params[0]->getValue() << '\n';
      if (!selectionProvider && state.selectedChannel != channels[0].get())
        throw std::logic_error("wrong selected channel");
      for (int i = 0; i < 4; ++i)
        params[i]->removeObserver(&watches[i]);
      continue;
    }
    if (!provider)
      mixer.doLink(channels[0].get(), link);
    else {
      int count;
      std::cin >> count;
      for (int i = 0; i < count; ++i) {
        int code;
        std::cin >> code;
        if (code == 0) {
          int from, to, inverse, g;
          std::cin >> from >> to >> inverse >> g;
          state.selectionGuard = g;
          links[from - 1]->setLink(*links[to - 1], inverse);
        } else if (code == 1) {
          int id, g;
          std::cin >> id >> g;
          state.selectionGuard = g;
          channels[id - 1]->removeLink();
        } else if (code == 2) {
          int id, tag, g;
          std::cin >> id >> tag >> g;
          state.selectionGuard = g;
          (void)channels[id - 1]->getParameterByTag(tag);
        } else if (code == 3) {
          int id, edit, g;
          unsigned bits;
          std::cin >> id >> bits >> edit >> g;
          state.selectionGuard = g;
          float f;
          std::memcpy(&f, &bits, 4);
          params[id - 1]->setValue(f, edit);
        } else if (code == 4) {
          int id, g;
          std::cin >> id >> g;
          state.selectionGuard = g;
          (id ? second : first).linkChanged();
        } else if (code == 5) {
          int g;
          std::cin >> g;
          state.selectionGuard = g;
          permission.auxLinkingChanged();
        } else
          throw std::logic_error("bad provider schedule");
      }
    }
    recording = false;
    std::cout << "RESULT " << trace.str() << '|' << state.selectionGuard << '|'
              << masters << ' ' << loads << ' ' << permissionsChanged << ' '
              << unsigned(bindings.dirty);
    for (int i = 0; i < 4; ++i) {
      float f = params[i]->getValue();
      unsigned bits;
      std::memcpy(&bits, &f, 4);
      std::cout << ' ' << bits;
      params[i]->removeObserver(&watches[i]);
    }
    std::cout << '\n';
  }
}
